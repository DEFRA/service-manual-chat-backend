# 2. Send the whole toolkit with every question

**Status:** accepted, 16 September 2026

## Context

The model has to answer from the AI Toolkit's guidance pages. The usual way is
retrieval: split the pages into chunks, embed them, store them in a vector
store and send only the closest chunks with each question. The early design
planned Titan embeddings with k-NN search, then PostgreSQL with pgvector.

At launch the toolkit was 43 pages, about 140,000 characters: about 26,000
tokens, against a context window of 1,000,000.

## Decision

Send every toolkit page, with the prompt, on every question. No chunking,
embeddings or store. The pages are baked into the image at the commit in
`CONTENT_REF` (`Dockerfile`).

## Consequences

- No retrieval step to build, run or get wrong: the model always has the page
  that holds the answer.
- An edit to a page or the prompt can be tried at once, locally, with nothing
  to re-index.
- Every question sends about 26,000 input tokens. Prompt caching was meant to
  cut the cost of a follow-up to about a tenth, but on CDP nothing is written
  to the cache (CAIT-317), so each question costs about 8p.
- A guidance change reaches Ask only when `CONTENT_REF` is bumped and the
  backend redeployed.

## Revisit when

- the toolkit outgrows the context window, or
- a comparison on the golden set shows retrieval answers better, or
- cost per question is too high at real volume.
