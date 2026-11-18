# 4. Use the service's own Bedrock guardrail

**Status:** accepted, 9 October 2026 · **Jira:** CAIT-308, CAIT-319

## Context

CDP attaches a Bedrock guardrail to every model call. The platform's shared
guardrail set all five content filters to HIGH. In user research it refused
fair questions, such as "Can I use ChatGPT on my Defra work?", as misconduct:
4 of 4 such questions, each at LOW confidence.

The options were the platform's shared LOW guardrail, which lowers all five
filters together and has no denied topics, or a guardrail of the service's
own.

## Decision

Use a guardrail of the service's own, set by CDP in cdp-tenant-config, with:

- the misconduct filter at LOW, and the other content filters at HIGH
- denied topics for medical, legal and financial advice
- personal data anonymised: replaced with a placeholder such as `{ADDRESS}`,
  not blocked

If a question that should be refused gets a bad answer at LOW, move
misconduct to MEDIUM. The content designer agreed the starting point.

## Consequences

- On dev, a check list of 26 questions was asked before and after the switch,
  on 15 and 16 October 2026. Before, the shared guardrail refused six fair
  questions as misconduct. After, the guardrail refused no fair question;
  three were still refused by the model. Every question that should be
  refused still was. CDP set up the same guardrail in test, perf-test and
  prod (CAIT-319).
- Anonymising catches some ordinary words: "UK" in a question is read as an
  address and reaches the model as `{ADDRESS}`.
- Not checked: whether anonymising also rewrites the model's reply. If it
  does, a quoted rule holding a masked word fails the word-for-word check and
  is dropped (see decision 6).
- On a `bedrock blocked the question` log line, `filters` lists every filter
  that acted, so an anonymising one such as `output:pii:NAME` can appear
  beside the one that blocked.
- Changing the guardrail is a request to CDP; we cannot change it ourselves.
- The guardrail and inference profile IDs differ in each environment: see
  the runbook, "Bedrock IDs per environment".
- The golden set runs without a guardrail, so it cannot show what the
  guardrail blocks. Refused questions are found from the logs: see the
  runbook, "When a fair question is refused".

## Revisit when

- a question that should be refused gets an answer, or
- the guardrail keeps refusing fair questions at low confidence.
