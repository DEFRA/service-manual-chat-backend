# Ask the toolkit: who and how

The roles around Ask the toolkit, the processes it runs on, and where its
assurance records are filed. Names and contact details are kept on Confluence,
not here, so they can change without a pull request: [Ask the toolkit: people
and contacts](https://eaflood.atlassian.net/wiki/x/DAbvggE).

For how to run the service, see [the runbook](runbook.md).

## Roles

Ask is in maintenance mode: keep it safe, patched, accurate and within budget,
with no new features. Three roles look after it day to day.

| Role | Looks after | Typical work |
| :-- | :-- | :-- |
| How it works (developer) | Both services' code, dependencies, deploys, the prompt and evaluation runs | Dependabot updates and security alerts, deploys through CDP, `CONTENT_REF` bumps, model moves |
| How it looks (interaction designer) | The Ask pages on the site | Changes to how answers, quotes and errors are shown; accessibility |
| How it speaks (content designer) | Answer quality, the golden set and the prompt's wording | Judging answers after a prompt or content change; keeping the golden set on Confluence current |

Occasionally needed:

- **Service owner or delivery manager**: change requests, approving spend on
  evaluation runs, keeping the ATRS record, DPIA and privacy notice current.
- **The delivery group's security representative**: whether a pen test or IT
  Health Check is needed after a material change.

## Teams outside ours

| For | Who | How |
| :-- | :-- | :-- |
| Platform, deploys, config, the guardrail, alerts | Core Delivery Platform (CDP) | `#cdp-support` on Slack |
| AWS credentials for evaluation runs | Cloud Centre of Excellence (CCOE), who run the Bedrock sandbox account | Ask for a key on the account named on the Confluence people page |
| The toolkit's content | AI digital toolkit team | The team mailbox |

## Processes

### Tickets

Work is tracked in the Jira project
[CAIT](https://eaflood.atlassian.net/browse/CAIT).

### A change to prod

1. Merge one pull request at a time. Two quick merges can collide on one image
   version.
2. Deploy to dev, then test, in the CDP portal. Ask one question on each.
3. Raise a change request in ServiceNow. The service owner approves it.
4. Deploy to prod and ask a known question (golden set row 6).

The runbook has the detail, including the config sync trap.

### Spending on evaluation runs

Runs use personal AWS credentials and cost real money: about £13.50 for a full
run, £40 to £50 for a prompt change. State the cost and get the service owner's
agreement before starting. [Evaluating Ask the toolkit](evaluation.md) says when
a run is needed.

### Routine

| Task | How often |
| :-- | :-- |
| Watch `#aice-team-alerts-prod` and `#aice-team-alerts-non-prod` | Daily, office hours |
| Read "Report a problem with this answer" emails; delete any holding personal data | Weekly |
| Dependabot updates and security alerts on both repos | Weekly |
| Usage against the daily ceiling and the Bedrock bill | Monthly |

### Access a new team member needs

- Write access on this repo and
  [service-manual-ui](https://github.com/DEFRA/service-manual-ui)
- The CDP portal and `cdp-app-config`
- The two Slack alert channels
- The team mailbox
- AWS credentials from CCOE, for evaluation runs

## Assurance records

These describe the service as it is now. A change to the model, the data kept or
who can use Ask means updating them before it goes live. They are not copied
or linked here.

| Record | Where it is filed |
| :-- | :-- |
| Production readiness review (PRR) | Held by the service owner, ask on Confluence |
| Algorithmic Transparency Recording Standard (ATRS) record | Held by the service owner, ask on Confluence |
| Data protection impact assessment (DPIA) | Held by the service owner, ask on Confluence |
| Privacy notice | [Published on the site](https://digital.defra.gov.uk/ai-toolkit/ask/privacy-notice) |
| IT Health Check (ITHC) | Held by the service owner, ask on Confluence |
