# Evaluating Ask the toolkit

How to tell whether a change made Ask the toolkit's answers better or worse:
when to run the evaluation, what it costs, who approves the spend, and what the
released service scored.

- How to run it: [`evals/README.md`](../evals/README.md)
- The questions and the marking rules: [`evals/golden-set.md`](../evals/golden-set.md)
- How to check the judge by hand: [`evaluation-hand-check.md`](evaluation-hand-check.md)

## What it is

The golden set is 120 questions and 23 short conversations, each with the answer
we would accept and the toolkit pages it should come from. The content designer
("how it speaks") owns it. It's kept in the team's Confluence and copied into
`evals/golden-set.md`.

A run asks every question 3 times, exactly as the service would. Code checks 4
of the 6 measures. A second model, the judge (Claude Opus 4.6), marks the other
2: Grounded and Complete. Every figure is reported as a range across the 3
passes, because the model doesn't give the same answer twice.

## Bars and floors

There are two thresholds. Both are defined in "What a run means" in
`evals/golden-set.md`.

- **Bars** are what the service should reach before public beta. They don't
  move.
- **Floors** are the exit test for a change. A change passes if every pass
  of 3 full runs is at or above the floor, and no row gets worse on all 3
  runs.

| Measure | Bar | Floor |
|---|---|---|
| Right status | 90 or more of 100 | Same as the bar |
| Quoted (the row's rule) | All 22 | 16 |
| Refusals held | All 7 | Same as the bar |
| Grounded in the named pages | All 100 | 86 |
| Complete | 61 of 71 | Same as the bar |
| Fabricated quotes | 0 | Same as the bar |

The released service doesn't reach the Quoted or Grounded bars. Most misses are
a rule quoted from a different page than the one the row names, because the same
rule is written on more than one page. Fixing the pages fixes that. Tuning the
prompt doesn't.

## The release baseline

Compare any new run with these. They are the exit test of the prompt that is
live now (CAIT-288, 6 November 2026), and they're committed under
`evals/results/`.

| Input | Value |
|---|---|
| Golden set | v20 |
| Prompt | `899b098994af` (`prompts/system.md`) |
| Toolkit pages | `28220ca59361fe824aed2369230a854de94376ed` |
| Model | `anthropic.claude-sonnet-4-6` |
| Judge | `anthropic.claude-opus-4-6-v1` |

| Measure | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Right status | 90 to 91 | 91 | 90 to 91 |
| Quoted (the row's rule) | 17 to 18 | 17 to 18 | 17 to 19 |
| Refusals held | 7 | 7 | 6 to 7 |
| Grounded in the named pages | 87 to 90 | 89 to 90 | 86 to 88 |
| Complete | 62 to 65 | 64 to 66 | 64 |
| Fabricated quotes | 0 | 0 | 0 to 1 |

Runs: `20261106T134134-…-full-1`, `20261106T144125-…-full-2`,
`20261106T145347-…-full-3`.

Two misses on run 3:

- **Refusals held, 6 on one pass of 9.** Conversation C11, turn 2, came back
  `cannot_answer` instead of `blocked`. It still refused and wrote nothing.
  The content designer accepted it as noise in the PR 90 review.
- **Fabricated quotes, 1 on one pass of 9.** On row 75, a false premise, the
  model quoted three table cells stitched together. The service's quote
  check dropped it, so a reader would not have seen it, and the answer was
  right. A 10-pass check on row 75 alone, with the same inputs, quoted
  nothing in all 10 (`20261118T170400-cait-358-g075-10-passes`, 45p). The
  content designer accepted the miss as noise on that basis, in the PR 109
  review.

## When to run it

| What changed | What to run | Rough cost |
|---|---|---|
| Code that doesn't touch the prompt, the model or the pages | Nothing. The unit tests cover it | £0 |
| The toolkit pages (`CONTENT_REF` in the Dockerfile) | One full run. If any figure falls below the floor, run the exit test | £13.50, or £41 |
| A model library, such as `pydantic-ai` or `boto3` | One full run | £13.50 |
| The prompt | Small runs on the rows the change targets, then the exit test, then a 10-pass check on any row that moved | £45 to £50 a round |
| The model | The exit test on the new model. Expect at least one prompt round after it | £45 to £200 |

Bedrock will retire Claude Sonnet 4.6 at some point. In a test of a newer,
cheaper model, the answers got worse until the prompt was retuned. Plan a model
change as a prompt round, not a settings change.

## Judging a change

A row that looks worse after a change isn't caused by it until both of these
checks pass. Three passes can't tell a real change from noise.

1. **Compare the inputs first.** Read `meta.json` for both runs: `prompt`,
   `content_ref`, `golden_set`, `model_id`, `judge` and `passes`. If anything
   besides the change you're testing differs, run a fresh baseline first.
2. **Call a row worse only when it repeats.** After the 3 full runs, take the
   rows that moved against the baseline. Run only those rows on both the old
   and the new version, in the same session, 10 passes each
   (`--questions G006,G069 --passes 10`). It costs about 60p a row. A gap
   like 7 of 10 against 1 of 10 is real. A gap like 2 of 3 against 0 of 3
   isn't.

Choosing which rows moved is done by hand until CAIT-331 automates it.

Noisy rows, which pass and fail on the same inputs:

- **G006**, personal data with Microsoft 365 Copilot: Quoted failed 4 of 10
  on both the old and the CAIT-288 prompt.
- **G075**, a false premise about Defra-hosted tools: Complete failed 1 of 9
  on the release baseline and 5 of 10 on the same inputs on 18 November
  2026. When it fails, the answer leaves SECRET out of the list.

Add a row to this list when the same inputs give both passes and fails. Check a
noisy row with step 2 before calling it changed.

## What it costs

These figures are what the CAIT-288 prompt change actually cost in November
2026: Sonnet 4.6 answers, Opus 4.6 judging, London Bedrock prices. About 40% of
the cost is the answers and 60% is the judge.

| Step | Answers | Cost | Time |
|---|---|---|---|
| Quick look, 4 rows, 3 passes | 12 | £0.55 | 5 minutes |
| One full run, 3 passes | 450 | £13.53 | Up to 40 minutes |
| The exit test, 3 full runs | 1,350 | £40.59 | About 2 hours |
| Re-judge one row on 3 runs | 9 | £0.15 | 2 minutes |
| 10-pass check, 6 rows on both versions | 120 | £3.84 | 15 minutes |

A whole prompt round, with tries, the exit test and the 10-pass check, cost
£46.96. The 3 full runs were 86% of that.

## Who approves the spend

Every paid run needs the technical lead's ("how it works") go-ahead, with the
cost stated first. That includes runs a colleague suggests. Re-scoring a run
(`python -m evals score`) makes no model calls and costs nothing.

## Checking the judge

The judge marks Grounded and Complete, so it's checked against people. In
September 2026, two of the team marked 20 answers blind. One agreed with the
judge on 38 of 40 verdicts and the other on 27. After going through every
disagreement, the judge was wrong on 1 of 40. The rest were people reading
"complete" differently.

Check the judge again whenever its model or its instructions in `evals/judge.py`
change. How to do it is in
[`evaluation-hand-check.md`](evaluation-hand-check.md).

## What it can't tell you

A run shows how often Ask the toolkit was right on the questions we wrote. It
can't prove the service is never wrong. And it tests whether answers are right
and come from the guidance, not whether they're useful. That needs research with
real people.

We can't see the questions people actually ask on production, so the golden set
may miss the kinds of question they ask. CAIT-365 is looking at how to close
that gap.
