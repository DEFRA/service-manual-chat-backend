# 7. The site waits for the answer in one call

**Status:** accepted, 16 September 2026

## Context

The site could wait for the whole answer, poll for it, or stream it as it is
written.

## Decision

The site posts the question to `POST /ask` and waits up to 30 seconds for the
whole typed answer. No polling or streaming.

## Consequences

- One request, one response: simple to build, test and log.
- Answers took a median of about 3.6 seconds in testing, well inside the
  limit.
- Streaming was not an option anyway: CDP's task role does not allow
  `InvokeModelWithResponseStream`.
- The backend allows Bedrock 25 seconds per call, and asks once more when an
  answer comes back in the wrong shape. In the rare worst case that takes
  about 50 seconds, so the site gives up first (CAIT-327).
- The site calls the backend without a token. Only services inside the
  platform can reach the backend, and the daily ceiling caps the cost. This
  was accepted for launch; adding authentication is CAIT-325.

## Revisit when

- answer times approach the 30 second limit.
