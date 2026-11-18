# 2. Send the whole toolkit with every question

**Status:** accepted, 16 September 2026

## Context

The model has to answer from the AI Toolkit's guidance pages. The usual way is
retrieval: split the pages into chunks, embed them, store them in a vector
store and send only the closest chunks with each question. The early design
planned Titan embeddings with k-NN search, then PostgreSQL with pgvector.

The toolkit is about 42 pages. Bedrock's own usage figures put a first
question, with the prompt and every page, at about 26,000 input tokens (25,866
on dev on 16 October 2026). This record assumes a context window of 200,000
tokens. The model may allow more, but whether CDP's inference profile does has
not been checked.

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

- the toolkit plus the prompt passes about half of the 200,000-token window,
  leaving too little room for the conversation and the answer, or
- a comparison on the golden set shows retrieval answers better, or
- cost per question is too high at real volume.
