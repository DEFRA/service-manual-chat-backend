# 5. Keep the conversation in the site, not the backend

**Status:** accepted, 16 September 2026; history widened 30 September 2026
(CAIT-290)

## Context

A follow-up question needs the earlier ones. The conversation could be kept by
the backend, in MongoDB, or by the site, which already has a session.

## Decision

The backend keeps nothing between requests. The site keeps the conversation in
its session (Redis on CDP, 4 hours) and sends the last 4 turns with each
question.

At first only the previous question was sent. User research found readers
referring further back, so it became the last 4 turns: 4, not 3, because a
golden set case asks "What was my second question?" after four questions.

## Consequences

- The backend needs no store for conversations, and nothing a reader typed is
  kept by it.
- The history goes in the user message, so the cached instructions stay the
  same on every call.
- Turns the guardrail or model refused are left out of the history, so a
  refused prompt cannot be replayed.
- A quoted rule is not sent in the history yet, so "say that rule again" fails
  (CAIT-300).
- `MAX_HISTORY_TURNS` must match in `app/ask/schemas.py` and service-manual-ui.

## Revisit when

- the backend needs history the site cannot send, or
- the call stops being synchronous (see decision 7).
