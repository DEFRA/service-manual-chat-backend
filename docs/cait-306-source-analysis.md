# CAIT-306: missing guidance links

Offline analysis on 9 November 2026, from backend checkout `e0ddfad`.
This is a write-up for the ticket, including agreement reported in the task
conversation on 9 November. It is not a record of deployment or Jira updates.
No model calls were made and no saved answers were changed or re-verified.

## Status and manual baseline

- Backend verification now includes a successfully checked quote's page in
  sources, using the corpus title, and deduplicates all sources by page URL.
- Invalid source URLs are repaired only on a unique exact corpus-title
  match, using the canonical URL/title and clearing the unverified section.
  Valid URLs and their metadata are unchanged. Repaired lists are
  deduplicated; unresolved and ambiguous references are dropped and logged.
  Repair logs use only canonical corpus URLs, never supplied titles or URLs.
  Quoted-rule citations are not repaired.
- Tests cover both `Answer` and `ModelAnswer`, rejected quotes, existing
  sources, source order, non-mutation and repeat verification.
- The original October question record has now been supplied. Job 8's links
  and job 3 turn 2 are "not noted", meaning unknown, not missing. Chris
  confirmed that current dev behavior is the relevant baseline.
- A user-supplied screenshot for "Can I use personal data with Microsoft 365
  Copilot?" shows a quote linked to Using data with AI, while Guidance used
  lists only Keeping data safe. The screenshot does not show the URL or
  deployed versions. No post-fix deployed validation has been performed.
- The supplied CDP screenshots show backend dev `0.48.0` and frontend dev
  `0.198.0`, rather than the review's backend `0.27.0`. These versions have
  not been independently queried, and the frontend/backend connection has
  not been confirmed.
- The dev frontend URL supplied through CDP is
  <https://service-manual-ui.dev.cdp-int.defra.cloud/ai-toolkit/ask>.

## Counting method

Run from the repository root:

```bash
uv run python -m evals sources evals/results/*
```

For a selected run, replace the wildcard with its directory. The command
prints JSON, including per-run denominators and affected question IDs,
model keys and pass numbers. It reads only saved metadata and answers; it
does not prepare credentials, fetch content, call a model or write into runs.

Only successful records with saved `verified.status == "answered"` count.
The source list is the saved `verified.sources`, not raw model output.
`G...` questions are first questions; `C...-tN` records are classified by
turn number, not by whether history is present. Empty and invalid source
data are not interchangeable: missing verified data fails explicitly.

The current evaluation writer does not save full unscored setup-turn
answers. Later history contains their words but not their sources.
Consequently, conversation setup first turns cannot be counted. First
questions below are the first-question records actually saved, not all
first turns that were called. Metadata for imported runs may not record
the question selection or setup count; the report marks those as null.

These are API source counts, not counts of the frontend's visible list:
the frontend further filters sources and removes a retained quote's page
from that list. A retained quote with a missing source is also counted
separately; it can overlap an empty list.

## Results

All 41 saved run directories were read, including historical/imported
baselines and targeted experiments. The inventory totals are:

| Saved reply type | Answered | No sources | Percentage |
| --- | ---: | ---: | ---: |
| First question | 4,545 | 2 | 0.04% |
| Follow-up | 1,083 | 41 | 3.79% |

Excluded: 3 failed calls and 2,070 replies with another status. These pooled
figures describe the saved inventory only: runs use different prompts,
content, question sets and repeated passes, so this is not a production
failure rate or a controlled before/after comparison.

Selected full runs, kept separate:

| Saved run directory | First: empty / answered | Follow-up: empty / answered |
| --- | ---: | ---: |
| `20261006T162946-cait-301-layout-in-code-run-e` | 0 / 233 | 3 / 53 (5.66%) |
| `20261106T114048-cait-288-round-two-items-3-4-full-1` | 1 / 257 | 3 / 67 (4.48%) |
| `20261106T123212-cait-288-round-two-items-3-4-full-2` | 1 / 258 | 3 / 69 (4.35%) |
| `20261106T124424-cait-288-round-two-items-3-4-full-3` | 0 / 257 | 3 / 66 (4.55%) |
| `20261106T134134-cait-288-round-two-item-3-try-2-full-1` | 0 / 258 | 3 / 69 (4.35%) |
| `20261106T144125-cait-288-round-two-item-3-try-2-full-2` | 0 / 258 | 3 / 67 (4.48%) |
| `20261106T145347-cait-288-round-two-item-3-try-2-full-3` | 0 / 259 | 3 / 68 (4.41%) |

The October full run provides historical context near the review date; it
is not the review's ten jobs. The last three runs are the latest full runs
in the checkout, each with three passes and the same recorded prompt hash
`899b098994af` and content ref `28220ca59361fe824aed2369230a854de94376ed`.
Their combined counts are 0 / 775 first questions and 9 / 204 follow-ups
(4.41%). Each run also records 78 unpersisted setup calls.

### What the empty lists actually represent

- **39 follow-up records are `C15-t5`: "What was my second question?"**
  They answer a conversation-memory question, not a guidance question.
  The latest three runs account for nine of these. In the latest run,
  pass 1 answers: `Your second question was "Is GitHub Copilot approved?"`
  Adding a guidance page would imply evidence the reply did not need.
- **Two follow-up records are `C14-t2`, passes 1 and 3 of
  `20260921T151604-imported`.** They redirect the reader back to the
  toolkit and refer to an earlier answer. These are historical outputs,
  not evidence that current dev still produces the review failures.
- **Both first-question records are `G027`.** These are pass 1 of
  `20261106T114048-cait-288-round-two-items-3-4-full-1` and pass 2 of
  `20261106T123212-cait-288-round-two-items-3-4-full-2`.
  The raw model lists a RAG page using
  `/ai-toolkit/tools/retrieval-augmented generation` (a space, not a hyphen).
  Verification removes it, leaving no sources. This is a malformed URL,
  not loss of previous-turn pages.

There is also one saved retained quote whose page is absent from sources:
`G003`, pass 2 of `20261005T172103-cait-291-baseline-v9`, quotes the Tools
page but lists only Using data with AI and Choosing a tool. This is a
separate count, not a newly validated quote against current content.

The review's job 3 "Our projects" result is a **wrong page**, not an empty
list. It must remain a separate issue. The records above do not establish
which saved row, if any, corresponds to that review job. Nonempty lists
have not been assessed for relevance by this count.

## Agreed recommendation

Do **not** copy the last answer's pages into every follow-up's displayed
list. The latest empty-list cases are memory-only replies, and a topic
change can make inherited pages misleading. These saved results do not
establish that missing history sources caused the six review failures.

The agreed and locally implemented code fix is **conservative canonical-URL repair**:

1. Keep corpus-backed URLs as the primary source identity.
2. For a rejected source URL only, permit resolution if its supplied title
   exactly matches one unique corpus page title.
3. Use that page's canonical URL and title; deduplicate by canonical URL.
4. With no unique exact title match, drop and log the reference with
   `no_title_match` or `ambiguous_title`. Do not guess from slugs, fuzzy
   titles, or the previous turn.
5. Log repair/drop outcomes without question, answer or quote text.

This directly targets the observed G027 failure without changing the
frontend history contract or system prompt. It does not claim to solve
every empty-list case. An exact title can still name an irrelevant page,
just as a valid model-supplied URL can; corpus membership is not proof of
relevance. Confirm canonical page availability against deployed content
when verifying the release.
The adjacent frontend checkout has one exact match for the raw G027 title,
`Retrieval-augmented generation (RAG)`, at the canonical hyphenated URL
`/ai-toolkit/tools/retrieval-augmented-generation`, which its markdown route
list also serves.

**Agreement reported on 9 November:** Farhana favored targeted repair over
carrying previous links forward, and Chris confirmed agreement. The backend
repair is implemented locally. No history change has been built. Other
missing-source cases on current dev should be assessed separately rather
than filled with inherited links.

## Frontend fix for AC1

The frontend previously had an intentional policy in
[`toViewModel`](../../service-manual-ui/src/server/ai-ask/answer.js):
it removed a retained quote's page from `sources` because the quotation
already linked to that page, so "Guidance used" never repeated it.

**Decision reported on 9 November:** keep both links. The quoted page must
appear in Guidance used as well as beneath the quote.

**Implemented on 9 November**, on the frontend's own
`cait-306-list-guidance-used` branch (based on `fcdd1da`):

- The filter that dropped the quote's own page from `sources` is removed;
  `usableSources` is used directly, so the quoted page is listed.
- `usableSources` now deduplicates by URL with a `Set`, so a page named
  twice (for example the quoted page repeated with a different section)
  is listed once. Unserved/unknown URLs are still dropped, unchanged.
- The quote's own attribution line in
  [`ask-answer.njk`](../../service-manual-ui/src/server/common/templates/partials/ask-answer.njk)
  ("From …") is untouched. No styling or history changes were made.
- `tests/unit/server/ai-ask/answer.test.js` was updated: the old
  "already-linked source is dropped" assertions now confirm the quoted
  source is retained and deduplicated.
- `tests/integration/server/ai-ask/controller.test.js` gained a case that
  renders a real answer page with `cheerio` and checks the quoted page's
  link appears once in `.app-ask__rule-source` and once in
  `.app-ask__sources`, alongside another known page, with an unknown page
  absent from both.

## Backend repair scope

**Title:** Repair malformed Ask source URLs using unique exact corpus titles.

**Status:** agreement received; implemented and tested locally on
`cait-306-list-guidance-used`. No separate external ticket has been created.

**Acceptance:** a rejected URL with one exact title match is repaired using
the corpus URL/title; valid URLs are unchanged; missing/ambiguous matches
are dropped and logged; repaired sources do not duplicate another source;
both API and model-answer verification paths are tested. Quoted-rule
validation is unchanged, and memory-only replies do not inherit pages.

This approach does not change what the frontend sends. If the agreed
solution instead carries pages in history, create a coordinated frontend/
backend ticket covering request schema, session storage, serialization,
evaluation history, topic changes, page validation and compatibility.
Do not include CAIT-300's quoted-rule history change.

## Remaining acceptance work

- **AC1:** backend and frontend both implemented and tested locally, on
  each repo's own `cait-306-list-guidance-used` branch. Neither is merged,
  deployed or reviewed yet, so the deployed-dev rendering check is pending.
- **AC2/AC3:** backend and frontend regression tests cover deduplication,
  rejected quotes and unserved pages.
- **AC4:** counts posted to CAIT-306 as a comment on 9 November, with the
  dev baseline screenshot for "Can I use personal data with Microsoft 365
  Copilot?" attached.
- **AC5:** recommendation recorded here and agreed by Chris and Farhana in
  the task conversation on 9 November; posted to CAIT-306 alongside AC4.
- Outstanding: open the backend and frontend PRs (linked to each other and
  to CAIT-306), get them reviewed, deploy, then repeat the dev baseline
  question to confirm both links render and resolve correctly, and record
  that deployed check on the ticket before closing it.
- The original six review cases from the 7 October detailed record have
  not been individually re-walked on current dev; Chris confirmed current
  dev behaviour is the relevant baseline rather than exact reproduction.

## Validation

The six focused missing-page/deduplication regression cases failed before
the production change. After it, 261 tests passed across corpus and quote
verification, Bedrock integration, the API router and all evaluation tests.
Ruff lint/format checks, targeted mypy checks and `git diff --check` passed.
Pylance found no syntax errors in the changed corpus code, corpus tests or
new source-analysis module.

Validation used the existing virtual environment, Python 3.14.3. The
repository pins 3.14.8; no interpreter or dependencies were changed.
No live Bedrock or deployed-dev validation was performed.

After adding URL repair, 283 tests passed across the same test selection.
Repair coverage includes unique exact matches, case/whitespace mismatches,
unknown and ambiguous titles, valid URL precedence, canonical deduplication
in either order, non-mutation, idempotence, privacy-safe logs and unchanged
quote validation. Ruff lint/format and targeted mypy checks passed again.

### Revalidation, 9 November, after the frontend fix

Backend: `pytest tests/app/ask tests/evals --no-cov` passed 352 of 352.
`ruff check`, `ruff format --check` and the targeted `mypy` run above all
passed again.

Frontend, on its own `cait-306-list-guidance-used` branch: `vitest run
tests/unit/server/ai-ask/answer.test.js
tests/integration/server/ai-ask/controller.test.js` passed 219 of 219.
`eslint` on the three changed files (`src/server/ai-ask/answer.js`,
`tests/unit/server/ai-ask/answer.test.js`,
`tests/integration/server/ai-ask/controller.test.js`) reported no issues.
Only these two files' test suites were run, not the frontend's full suite
or its stylelint/coverage checks.

No commit, PR, merge, deployment or live Bedrock/dev check was made for
either repo as part of this revalidation.
