# 8. The site calls the backend without a token, for launch

**Status:** accepted for launch, 15 October 2026, as a known security gap ·
**Jira:** CAIT-325

## Context

The backend has one endpoint, `POST /ask`, which spends money on Bedrock.
Before launch the plan was for the site to sign each call, as it already does
for its calls to the triage service. It was not built in time.

## Decision

Launch with the site calling the backend without a token. The service team
accepted this on 15 October 2026 and recorded it in the production readiness
review (PRR), item 4B, with authentication promised in the first week after
launch (CAIT-325).

It was accepted because:

- the backend is reachable only from services inside the CDP platform, not
  from the internet
- the daily ceiling (600 Bedrock requests by default) caps the cost of any
  misuse, at about £50 a day

## Consequences

- Any service inside the platform could call the backend and spend up to the
  daily ceiling. A day at the ceiling also stops Ask answering readers.
- The PRR promise is not yet met: CAIT-325 had not started on 17 November
  2026.

## Revisit when

- CAIT-325 is done (this record is then superseded), or
- the backend becomes reachable from outside the platform, or
- the daily ceiling is reached on a day without matching reader traffic.
