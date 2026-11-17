# 3. Answer with Claude Sonnet 4.6

**Status:** accepted, 17 September 2026

## Context

The model has to quote a rule word for word, choose the right kind of answer
(one of six statuses) and cite the right page. It must be on CDP's list of
enabled Bedrock models.

We compared Claude Sonnet 4.6, Claude 3 Haiku, Amazon Nova Pro, Nova Lite and
GPT-OSS 120B, with Claude Opus 4.6 as a yardstick. Llama 3 70B could not run:
its window is too small and it has no tool use. The same day, the golden set
(100 questions) was run on the models that could be deployed.

| | Sonnet 4.6 | Others |
| :-- | :-- | :-- |
| Rules quoted that passed the word-for-word check, first comparison | 18 of 21 | 1 or 2 of 21 (Haiku, Nova Pro, Nova Lite) |
| Right status, golden set | 85 of 100 | 59 to 64 |

Sonnet matched Opus on every check code could make, at about 60% of the
price.

## Decision

Answer with Claude Sonnet 4.6, through the service's own inference profile in
each environment. A model that rewords a rule is ruled out whatever it costs.

## Consequences

- About 8p a question without the prompt cache; about 1p for a cached
  follow-up if CAIT-317 is fixed.
- Median answer time was about 3.6 seconds.
- Claude Sonnet 5 was tried in October 2026: about 14% cheaper per question,
  but more literal on a prompt written for 4.6. Moving needs a prompt round
  and a full golden set run first. Whether it is on CDP's enabled list was not
  checked.

## Revisit when

- Sonnet 4.6 is announced for deprecation on Bedrock, or
- cost per question needs cutting, and the golden set shows a cheaper model
  or route does not hurt answers.
