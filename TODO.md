# To Do

`POST /ask` works locally against the stub and the Bedrock sandbox, and the
front end on `main` calls it when `AI_TOOLKIT_ASK_API_URL` is set. Work with
a ticket lives in Jira under CAIT; this list is only what has none.

## Ask the toolkit

- **Conversations.** `conversation_id` is accepted and ignored;
  `previous_question` carries the whole context. Enough for the local loop,
  not for the follow-up flow the front end is building. Whether the
  conversation lives here (Mongo is already wired) or in the front end's
  session is under team review; the ticket follows the decision.

In Jira: prompt caching (CAIT-279), the quote check (CAIT-280), the prompt
fix for the seven failure patterns (CAIT-281), deploy to CDP dev including
the Mongo ping at boot and mapping a guardrail intervention to `blocked`
(CAIT-282), repeatable evaluation (CAIT-283), clearing the template's
example routes, Sonar and dependabot (CAIT-284).

## Template chores

Left over from the CDP Python template. No deadline on either.

- A Python base image including the self-signed cert. Partially done: certs
  are loaded from environment variables, as in the Node template.
- `--no-access-log` is set in the `Dockerfile`
  ([uvicorn docs](https://www.uvicorn.org/settings/#logging)). A finer
  approach that only silences `/health` is described in
  [starlette#864](https://github.com/encode/starlette/issues/864).
