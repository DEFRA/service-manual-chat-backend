# Ask the toolkit: runbook

For whoever runs Ask the toolkit, including people who did not build it. Ask is
two services on the Core Delivery Platform (CDP):

- [service-manual-ui](https://github.com/DEFRA/service-manual-ui), the public
  site. Ask lives under `/ai-toolkit/ask`, behind `AI_TOOLKIT_ASK_ENABLED`.
- this backend, which answers `POST /ask` from the toolkit's own pages with
  Claude Sonnet 4.6 on Amazon Bedrock.

The site's README has the short version: its settings, how to turn Ask off, and
what to do first when something goes wrong. This page adds how the service fits
together, the known issues, and who to ask.

## How a question is answered

1. A reader types a question, at most 500 characters. The site keeps the
   conversation in its Redis session for 4 hours, up to 20 questions.
2. The site sends the question and the last 4 turns to `POST /ask`. It waits
   30 seconds at most.
3. The backend adds one to the day's count in MongoDB. Past the ceiling (600
   a day by default, reset at midnight UTC) no model is called.
4. The backend sends the toolkit pages, its prompt and the question to
   Bedrock through CDP's outbound proxy, using the service's own inference
   profile and guardrail.
5. The model replies as a typed answer: `answered`, `need_more_detail`,
   `cannot_answer`, `talk_to_a_person`, `blocked` or `error`, with any rule
   quoted word for word and links to the pages it used.
6. The backend checks every quote is really on the page it names and drops
   any source that is not a toolkit page, then returns the answer.

Every failure returns a typed answer, never a 5xx: the reader sees "The toolkit
could not answer just now" with their question kept.

The toolkit pages are baked into the image at build time from service-manual-ui
at the commit in `CONTENT_REF` (`Dockerfile`). The prompt is
`prompts/system.md`, also in the image.

## Where things live

| What | Where |
| :-- | :-- |
| Settings per environment | `services/service-manual-chat-backend/<env>/` and `services/service-manual-ui/<env>/` in cdp-app-config (internal) |
| Inference profile and guardrail IDs | The same backend env files, and the CDP portal: the service's Resources tab |
| Guardrail settings | Run by CDP. The service's own guardrail is the same in every environment. The portal does not show its version number yet. |
| Logs | OpenSearch on CDP, for both services, kept 6 weeks. CDP also keeps them in S3 indefinitely, which only the platform team can open. The platform does not keep readers' public IP addresses. |
| Alerts | Grafana on CDP. See [Alerts](#alerts). |
| Every question and answer | Bedrock invocation logging, turned on by the platform: 30 days, unmasked, in a restricted S3 bucket. We cannot change it. |
| The day's count | MongoDB, the backend's only stored data |
| Toolkit pages | service-manual-ui `src/content`, at `CONTENT_REF` |

## Deploying

Deploy from the CDP portal. Two things have caught us out:

- **The first deploy after a config change can keep the old config.** After a
  cdp-app-config change merges, check the portal shows the new config for
  that environment before deploying, or deploy a second time. Then check one
  question is answered.
- **Merge one backend PR at a time.** Each merge to `main` builds and tags a
  new version. Wait for that build to finish before merging the next, or two
  merges can collide on one version.

Order: dev, then test, then prod. Perf-test is for performance tests, not
readers.

## Turning it off

In the order the site's README gives:

1. `ASK_DAILY_CEILING=0` on this backend, then redeploy. No model is called;
   readers are told to try again tomorrow.
2. `AI_TOOLKIT_ASK_ENABLED=false` on the site, then redeploy. The Ask pages
   return 404.

Neither is instant: each needs a config change and a deploy. There is no runtime
switch.

## Alerts

All route to `#aice-team-alerts-prod` and `#aice-team-alerts-non-prod`, watched
in office hours. Ask is on CDP's lowest tier: no out-of-hours support and no
PagerDuty.

| Alert | Fires when | First check |
| :-- | :-- | :-- |
| CDP defaults, both services | 5xx responses, tasks not running, CPU, memory or storage above 80%, log ingestion errors | The service's logs in OpenSearch |
| Response time, both services | p95 above 20,000 ms over 10 minutes | Bedrock slow or failing; the backend's `bedrock gave no answer` lines |
| No answer | More than 2 error answers in 15 minutes | MongoDB down, or Bedrock or the proxy failing |
| Half the daily ceiling | More than 300 calls in 24 hours | Genuine use, or a script? |
| Daily ceiling reached | The ceiling is hit | Ask has stopped answering until midnight UTC |

The three log alerts are in the `service-manual-chat-backend advanced` group.
They count log lines, not error levels: the backend logs one line at error level
on every start-up, so an alert on error level would fire on every deploy.

## Reading the logs

The backend never logs a question or an answer. Per question it logs:

| Log line | Means |
| :-- | :-- |
| `ask question_length=… history_turns=…` | A question arrived |
| `bedrock answered model=… status=… input_tokens=… output_tokens=…` | Answered, with the status the model chose and the tokens used |
| `bedrock blocked the question … filters=…` | The guardrail stopped it. `filters` names the policy, such as `input:topic:Legal advice` |
| `bedrock could not connect, trying once more` | The proxy or Bedrock connection failed; one more try follows |
| `bedrock gave no answer` | No answer, with the cause: timeout, throttling, a reply that never validated, or a connection that failed twice |
| `ask daily ceiling reached` | Past the day's ceiling |
| `ask daily usage counter unavailable, refusing the call` | MongoDB cannot be reached, so every question is refused |
| `Dropped N sources not in the corpus` | The model named a source that is not a toolkit page; it was removed |

A warm question costs about 1p and a cold one about 8p: see "What a question
costs" in the README.

## Known issues

- **The guardrail can block a fair question.** The platform's shared
  guardrail refused fair questions (such as "Can I use ChatGPT on my Defra
  work?") as misconduct. The service's own guardrail fixes the known cases,
  but any guardrail can still refuse something it should not. The reader
  sees "This question cannot be answered here." To check, find the
  `bedrock blocked the question` line and its `filters`, and raise it with
  CDP in #cdp-support.
- **The model sometimes refuses a fair question itself.** Separate from the
  guardrail: the status is `blocked` on a `bedrock answered` line. Fix it in
  the prompt, then run the golden set (see `evals/README.md`) before
  releasing.
- **A rule is sometimes quoted from the wrong page.** The quote check stops a
  made-up quote but not a real rule credited to a different page. Seen on a
  few golden set rows on some runs, within the noise of the measure.
- **A brief outbound proxy failure.** Before 0.37.0 one failed connection to
  CDP's proxy gave the reader an error. The backend now tries once more, and
  that attempt counts once against the ceiling. If `bedrock could not
  connect` lines start to cluster, raise it with CDP.
- **Guidance changes are not picked up on their own.** Answers come from the
  pages at `CONTENT_REF`. After a guidance change on service-manual-ui, set
  `CONTENT_REF` to the new commit on its `main`, merge, and redeploy the
  backend.
- **A reader blocked by CDP's WAF sees a plain "403 Forbidden".** The WAF is
  platform wide (AWS common rules, known bad inputs, Bot Control) and
  answers with its standard 403 and no custom response body, so the reader
  gets no GOV.UK page and no way to contact us. A reader who reports a
  bare 403 was probably stopped there, before the site; ask CDP.
- **The site and backend logs cannot yet be joined by request ID.** The site
  does not pass `x-cdp-request-id` on to the backend. Match on time instead.
- **Some answers assume the reader works at Defra.** For example, an answer
  about an incident can point to a route only Defra staff can use. Found in
  user research; cases are being added to the golden set.
- **The site calls the backend without a token.** Only services inside the
  platform can reach the backend, and the daily ceiling caps the cost.
  CAIT-325.
- **The daily counter's documents never expire.** One is kept for each day.
  CAIT-313 adds a 90 day expiry.
- **The Ask journey test can fail on dev when the answer is fine.** Its
  "answer with a source link" check waits about 6 seconds for the click,
  and dev answers can take longer. Look at the answer before treating it as
  a fault.

## Changing the prompt or the model

Run the golden set before and after: `evals/README.md` says how, what the six
bars are, and what a run costs. Runs use a Bedrock sandbox key, not CDP, so they
do not count against the service's ceiling. A full run with the judge costs
about £13.50; get the spend agreed first.

## Problem reports

"Report a problem with this answer" emails the question, the answer and the
reader's note to the team mailbox through GOV.UK Notify. Treat that text as
untrusted. If a reader typed personal data, follow [report an AI
incident](https://digital.defra.gov.uk/ai-toolkit/guidance/report-an-ai-incident)
and delete the report email.

## Who to ask

| For | Ask |
| :-- | :-- |
| Platform, deploys, config, the guardrail, alerts | CDP, in #cdp-support on Slack |
| A Bedrock sandbox key for evaluation runs | The Cloud Centre of Excellence (CCOE), who run the sandbox account |
| Whether a pen test or IT Health Check is needed | The delivery group's security rep |
| The toolkit's content | The AI digital toolkit team, through the team mailbox |
| Tickets | Jira project CAIT |
