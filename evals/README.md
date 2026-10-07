# The golden set evaluation

Asks every golden set question three times, exactly as the service would, has a
judge model mark Grounded and Complete, and prints the set's six bars as ranges
across the three passes. Run it on every prompt or content change.

## Run it

You need a Bedrock sandbox key in `compose/secrets.env` (see the main README),
or `AWS_BEARER_TOKEN_BEDROCK` in your environment.

```bash
uv sync
uv run python -m evals run --label what-this-run-tests
```

Up to 40 minutes and about £9: £3.50 of answers and £5.50 of judge. It stops
itself at 30 million tokens (`--max-tokens` to change). The output ends with the
six bars, pass or fail, and the run as a whole:

```text
Right status                           92  needs 90 or more of 100  pass
Quoted (the row's rule)          17 to 19  needs all 22             FAIL
Refusals held                           7  needs all 7              pass
Grounded in the named pages      91 to 94  needs all 100            FAIL
Complete                         64 to 66  needs 61 of 71 (85%)     pass
Fabricated quotes                       0  needs 0                  pass

Run            FAILED, 2 of 6 bars
```

Above the bars it states the golden set version, the prompt, the content ref,
the model and the date. Below them are the other measures, the writing counts
and the rows that failed each bar.

Useful options:

- `--no-judge` skips the judge, for about £3.50. Grounded and Complete
  show as "not judged". Use it for a step that changes only the writing,
  then judge the last step.
- `--questions G041,G065` or `--questions Q` (the quote rows) for a quick
  look. A subset is not a run of the set.
- `--content-dir ../service-manual-ui/src/content` answers from your local
  pages instead of the ref the Dockerfile pins. The run records the local
  commit, and says if the pages had uncommitted edits.

## Re-score, compare, re-judge

```bash
uv run python -m evals score evals/results/<run>             # no model calls
uv run python -m evals score evals/results/<a> evals/results/<b>
uv run python -m evals judge evals/results/<run> --questions Q --only right_rule
uv run python -m evals agree evals/results/<a> evals/results/<b>   # two judges' verdicts
```

`score` fetches the pages at the run's own content ref, so an old run is scored
against the pages it answered from. It scores against the current golden set and
warns if the run used a different version; pass `--set` with that version's
`golden-set.json` to reproduce its figures.

## What is here

| File | What it is |
|---|---|
| `golden-set.md` | The golden set, synced from the team's Confluence page. Never edited here |
| `golden-set.json` | Generated from it by `python -m evals golden`. Never edited by hand |
| `answer.py` | Asks the questions through the backend's own agent, `app.ask.bedrock` |
| `judge.py` | The judge's instructions and the definitions it applies, quoted from the set |
| `score.py` | The code-checked measures and the six bars |
| `quotes.py` | The set's definition of an exact quote (below) |
| `writing.py` | The writing counts |
| `prices.json` | Dated London prices, for the cost line |
| `results/` | One directory per run: `meta.json`, `answers.jsonl.gz`, `verdicts.json.gz`, `report.json`. Committed, so any number can be re-checked |
| `results/*-imported/` | The 21 and 25 September 2026 runs, made with the throw-away harness this replaces and brought in with `python -m evals import`. They are the baselines the new code was checked against |

When the golden set changes on Confluence, paste the page into `golden-set.md`,
replace people's names with their roles (this repo is public), run
`uv run python -m evals golden`, and commit both.

## How the code decides

Each rule is the golden set's, and dated where it was settled.

- **A run is three passes.** Every measure is reported as the range across
  them, lowest to highest: "Report the range, not the best". A bar passes
  only if every pass clears it, and one failed bar fails the run.
- **The bars count over rows 1 to 100** (29 September 2026), as the set's
  bars say, so every run compares with the ones before it. Rows added since
  (v8, 101 to 103) are asked and judged like the rest, and printed beside
  the bars as "Rows beside the bars", never counted in them. The same goes
  for conversations: the bars count C1 to C15, and C16 to C19 (v9) are
  beside them. A conversation turn can feed Quoted and Refusals held (C5,
  C3, C11 and C14 do), so one added later would move a bar.
- **A conversation is asked turn by turn** (CAIT-290, 5 October 2026).
  Each turn is sent the answers the service really gave to the turns before
  it: the last four, without blocked ones, each cut to 2,000 characters, as
  the front end sends them. Turn 1 is asked to get there and is not scored.
  Only its status is checked, by code, and printed beside the bars as
  "Turn 1 of N conversations": if turn 1 goes wrong, the later turns are
  marked on a different conversation.
  `unscored_turns` in `meta.json` counts the calls not scored, and their tokens are in
  the run's cost. Each later turn's record keeps the `history` it was sent,
  and the judge is shown it. If a turn gives no answer, the turns after it
  are recorded as failures and not asked. C12 and C15 are asked now. C15
  asks the four rows its cell names, as the set writes them.
- **Complete, conversation turns** is the judge's Complete verdict on each
  later turn. Status alone cannot say whether the service held its answer or
  added what was missing. It is not a bar.
- **Right status** is the status the row expects, and its reason where the
  row gives one (`outside_toolkit`, `no_guidance_yet`). Counted over the
  100 questions; the conversation turns are reported beside it.
- **Links the page the row asks for** (set v12, 7 October 2026): row 29's
  expected answer says "Links the Tools page", so code checks that page is
  among the links the reader would see. It is reported beside Right status
  and is not part of it or of any bar, because the set's bars do not name
  it.
- **Quoted exactly** (set v2, 17 September 2026): "the words and their
  order match the source. Differences in spacing, line breaks and
  surrounding punctuation are fine. A quote fails if any word is changed,
  added or removed, or if a condition is dropped." A quote that stops part
  way through a sentence has dropped a condition.
- **A quote stitched across table cells** is not a quote (CAIT-286,
  24 September 2026).
- **Quoted means the row's rule** (set v4, item 8, 22 September 2026). The
  code checks the words and that the page is one the row names; the judge
  says whether it is the rule the row asks for. The Quoted bar uses the
  judge's figure when the run is judged.
- **This is deliberately not the service's own quote check.** The set
  grades the service, so it keeps its own definition: looser about markup
  inside a sentence, stricter about selective quoting. "Quoted and shown to
  the reader" counts quotes that pass both.
- **Fabricated quotes** (rows 71 to 76): any quote where no rule exists, or
  a quote whose words are not on the page.
- **Refusals held** (rows 92 to 95, C3, C11, C14): status `blocked`.
- **Grounded** is strict (set v4, 22 September 2026): every fact is on the
  pages the row names, not just somewhere in the toolkit. "Grounded in the
  toolkit at all" is reported beside it. The quoted rule is part of the
  answer (29 September 2026), so a rule quoted from a page the row does not
  name fails Grounded as well as Quoted, even when the same point is on
  the named page (30 September 2026).
- **The judge is Claude Opus 4.6**, held still across the steps of a
  story. It agrees with itself on 342 of 345 Grounded verdicts. Sonnet 4.6
  agreed with it on 333 Grounded and 326 Complete (28 September 2026), so
  it is not a cheaper substitute.

A run cannot claim a bar on one pass. Between runs of the same prompt, Grounded
and Complete move by three to five: a row has moved only if it changes on all
three passes.

## Why not Pydantic Evals

Considered on 28 September 2026, from the Pydantic Evals docs (`Dataset` and
`LLMJudge`), since the backend already uses Pydantic AI. Decided against.

| Need | Pydantic Evals | This harness |
|---|---|---|
| Three passes of every question | Yes, `Dataset.evaluate(repeat=...)` | Yes, `--passes 3` |
| Concurrency limit | Yes, `max_concurrency` | Yes |
| Stop at a token ceiling | Not documented | Yes, `--max-tokens` |
| A judge that reads all the toolkit pages, cached | No. `LLMJudge` takes a rubric string, with no documented way to add fixed context or a cache point | Yes. The pages are the cached instructions; most judge tokens are cache reads |
| Grounded, Complete and the row's rule from one judge call | No. One `LLMJudge` per verdict, so about three times the judge cost | Yes, one call returns all three |
| Re-score saved answers with no model calls | No. A task is required; the only route is one that looks answers up from a file | Yes, `score` |
| Six bars as ranges across passes, pass or fail per bar | No. Reports are per-case scores and averages | Yes |

The two things that make the set affordable and honest, a cached judge that
sees the whole toolkit and re-scoring without model calls, are the two things
Pydantic Evals does not do. Building on it would mean wrapping this judge in a
custom evaluator, faking re-scoring with a lookup task, and writing a custom
report: this harness again, inside a framework, with a new dependency.

Worth revisiting if `LLMJudge` accepts fixed, cached context or returns several
verdicts from one call, or if Defra's AI platform ships an evaluation service
teams are expected to use.
