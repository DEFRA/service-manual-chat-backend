# 1. The backend is Python FastAPI with Pydantic AI

**Status:** accepted, 10 September 2026

## Context

Ask the toolkit needed a backend on CDP to call Amazon Bedrock. Until Defra's
"paved road" AI platform is ready, the brief was to follow the pattern of
DEFRA/aice-triage-automation: a thin API service, a switch between a stub and
Bedrock, Bedrock reached through an inference profile and guardrail on CDP.

aice-triage-automation is Node. The early design notes named both Python and
Node for this backend. The nearest existing service of this kind, the RPA
guidance service, is Python, and the paved-road team expected to use Pydantic
AI.

## Decision

The backend is a Python FastAPI service using Pydantic AI, built on CDP's Python
backend template. We borrow aice-triage-automation's pattern, not its language.

The front end stays Node: it is part of service-manual-ui (Hapi, Nunjucks,
GOV.UK Frontend).

## Consequences

- The Python backend template needed a restricted scope from CDP, unlike the
  self-serve Node template.
- A maintainer needs both Python and Node.
- The Pydantic AI agent is kept apart from the FastAPI plumbing, so a move to
  the paved-road platform should be a re-host, not a rewrite.
- Evaluation tools come from the Python ecosystem (`evals/`).
