"""Grounded, Complete and the right rule, marked by a judge model, pass or fail.

The definitions are quoted from golden-set.md. The judge sees the question,
the expected answer, the named source pages, the whole toolkit and the answer
as a reader would be shown it. It never sees which model wrote the answer.
Status and the words of a quote are not judged here: code checks those.
Whether the quoted rule is the one the row asks for is (set v4, item 8).
The quoted rule counts for Grounded (settled 29 September 2026): the judge had
passed 13 and failed 8 of 21 wrong-page quotes when the prompt did not say.
Even when the same point is on the named page (30 September 2026): the judge
passed J06 because its quote added no new facts, then because row 4 expects
no quote. The reason comes before the verdicts (30 September 2026): J06's
reason once ended "This fails" after the verdict was written as a pass.

The judge is held still across the steps of a story, so bars are comparable.
Opus 4.6 agrees with itself on 342 of 345 Grounded verdicts; Sonnet 4.6
agreed with Opus on 333 and on 326 of 345 Complete, so it is not a
substitute (28 September 2026).
"""

import asyncio
import json

from pydantic import BaseModel

from evals.runs import Budget, read_answers, read_verdicts, write_verdicts

JUDGE_MODEL_ID = "anthropic.claude-opus-4-6-v1"
CONCURRENCY = 6

PROMPT = """You are scoring one answer from "Ask the toolkit", a question and answer
service on the Defra AI digital toolkit website, against a golden set written
before anyone saw model output. The toolkit pages are below. Score three
things, each pass or fail, exactly as the golden set defines them.

Grounded. "Is every fact in the answer traceable to the named source pages?
An answer that is true but not on those pages fails. That is the model
answering from its own knowledge, and we cannot stand behind it."
Give two verdicts:
- grounded_in_named_sources: every fact is on the pages named for this
  question. When the named sources are "none", pass only if the answer
  asserts no facts beyond saying what the toolkit does and does not cover and
  where to go next.
- grounded_in_toolkit: every fact is on some toolkit page, named or not.
An answer that declines, asks for more detail or refuses, and states no
facts, is grounded.
The quoted rule is part of the answer. A rule quoted from a page not named
for this question fails grounded_in_named_sources, even when the message
around it is grounded, even when the same point is on the named page, and
whether or not a quoted rule is expected for this question.

Complete. "Does the answer contain the claim in the Expected answer column?
Citing the right page is not enough. If the column says 'no, and remove it
first', an answer that links to the page without saying no fails."
The claim may be in the message, in the quoted rule, or in the options. Where
the expected answer says something must appear or must not happen, hold the
answer to that. If the answer chose a different status from the one expected
and so never makes the claim, it is not complete.

Right rule. "Quoted means the rule that row asks for. A different rule that
happens to be true, and is genuinely on one of the named pages, is Complete
at best." Only when the question says a quoted rule is expected and the
answer carries a rule_verbatim: is the quoted text the rule the Expected
answer states? Otherwise leave right_rule null. Three rules for this verdict:
- The row's rule is what the Expected answer states. A quote passes when the
  passage it quotes makes a claim the Expected answer states. It fails when
  the passage makes a claim the Expected answer does not state, however apt:
  a warning from the top of the page is not the four steps below it, and a
  supporting detail is not the rule it supports.
- "Where a rule is written on more than one page in different words, each
  page's wording passes on its own page." When several pages are named, the
  set's authors have checked that each carries the row's rule in its own
  words. A quote of that passage from any named page passes, however far its
  wording sits from the Expected answer's.
- Judge which rule it is, not its wording and not whether the answer is
  complete. The code has already checked the words, and Complete is scored
  above. A quote of the right rule passes even when the message around it
  leaves something out, and a quote of the wrong rule fails even when the
  message states the right one.

Do not reward length or tone. Write the reason before the verdicts: one
sentence naming the fact or claim that decided a fail, or "nothing" if all
pass. The verdicts must follow from it."""


class Verdict(BaseModel):
    # The reason comes first so the verdicts follow from it (30 September 2026).
    reason: str
    grounded_in_named_sources: bool
    grounded_in_toolkit: bool
    complete: bool
    right_rule: bool | None = None


def merge_verdicts(
    existing: list[dict], fresh: list[dict], only: list[str] | None = None
) -> list[dict]:
    """Fresh verdicts over existing ones by (key, run, question). With `only`, take just
    those fields from a fresh verdict, its reason filed as <field>_reason."""
    merged = {(j["key"], j["run"], j["question_id"]): j for j in existing}
    for j in fresh:
        key = (j["key"], j["run"], j["question_id"])
        if only and key in merged:
            marks = dict(merged[key]["marks"])
            for field in only:
                marks[field] = j["marks"].get(field)
                marks[f"{field}_reason"] = j["marks"].get("reason")
            merged[key] = {**merged[key], "marks": marks}
        else:
            merged[key] = j
    return list(merged.values())


def said(turn: dict) -> str:
    options = f" Options: {'; '.join(turn['options'])}" if turn["options"] else ""
    return (
        f"Reader: {turn['question']}\n"
        f"Service ({turn['status']}): {turn['message']}{options}"
    )


def shown_to_judge(record: dict, question: dict, titles: dict[str, str]) -> str:
    """The answer as the reader saw it, except the quote: the raw one the model gave,
    because the old backend check dropped true quotes as misquotes (CAIT-280), and
    which rule was quoted is what right_rule judges."""
    asked = f"Question: {question['question']}"
    history = record.get("history")
    earlier = question.get("earlier")
    if history:
        # What the service was sent: its own real answers to the turns before.
        asked = (
            "The conversation so far, as the service was sent it:\n"
            + "\n".join(said(turn) for turn in history)
            + f"\n\nQuestion (turn {len(earlier or history) + 1}): {question['question']}"
        )
    elif earlier:
        # A run from before conversations were asked turn by turn.
        asked = f"Question: (follow-up to: {earlier[-1]}) {question['question']}"
    pages = question.get("expected_pages")
    if pages is None:
        named = "not named for this question; use the whole toolkit"
    else:
        named = ", ".join(f"{titles[url]} ({url})" for url in pages) or "none"
    shown = {**record["verified"], "rule_verbatim": record["answer"]["rule_verbatim"]}
    return (
        f"{asked}\n"
        f"Expected status: {' or '.join(question['expected_status'])}\n"
        f"Expected answer: {question['expected_answer']}\n"
        f"Quoted rule expected: {'yes' if question.get('expects_rule') else 'no'}\n"
        f"Named source pages: {named}\n\n"
        f"Answer to score:\n{json.dumps(shown, indent=2, ensure_ascii=False)}"
    )


async def judge(
    run,
    questions: dict[str, dict],
    budget: Budget,
    *,
    judge_model: str = JUDGE_MODEL_ID,
    only_questions: list[str] | None = None,
    only_fields: list[str] | None = None,
) -> dict:
    """Judge a run's answers and merge the verdicts into verdicts.json.gz.
    Returns a summary for meta.json."""
    from pathlib import Path

    from pydantic_ai import Agent
    from pydantic_ai.models.bedrock import BedrockConverseModel, BedrockModelSettings
    from pydantic_ai.providers.bedrock import BedrockProvider

    from app.ask.corpus import as_context, load_corpus
    from app.config import config

    corpus = load_corpus(Path(config.content_dir))
    titles = {url: page.title for url, page in corpus.items()}
    the_judge = Agent(
        BedrockConverseModel(
            judge_model, provider=BedrockProvider(region_name=config.bedrock_region)
        ),
        output_type=Verdict,
        instructions=f"{PROMPT}\n\n# The toolkit pages\n\n{as_context(corpus)}",
        model_settings=BedrockModelSettings(bedrock_cache_instructions=True),
        retries=2,
    )
    records = [r for r in read_answers(run) if r["ok"]]
    if only_questions:
        records = [r for r in records if r["question_id"] in only_questions]
    limit = asyncio.Semaphore(CONCURRENCY)
    tokens = dict.fromkeys(
        ("input_tokens", "cache_read_tokens", "cache_write_tokens", "output_tokens"), 0
    )

    async def score(record: dict) -> dict | None:
        async with limit:
            if budget.exhausted:
                return None
            try:
                result = await the_judge.run(
                    shown_to_judge(record, questions[record["question_id"]], titles)
                )
            except Exception as error:  # noqa: BLE001
                print(
                    f"  judge failed on {record['question_id']} pass {record['run']}: {error}"
                )
                return None
        budget.spend(result.usage)
        for name in tokens:
            tokens[name] += getattr(result.usage, name)
        return {
            "key": record["key"],
            "run": record["run"],
            "question_id": record["question_id"],
            "marks": result.output.model_dump(),
        }

    # One call first so the cache is written once, not six times.
    first = [await score(records[0])] if records else []
    rest = await asyncio.gather(*(score(r) for r in records[1:]))
    fresh = [j for j in first + list(rest) if j]
    merged = merge_verdicts(read_verdicts(run), fresh, only_fields)
    write_verdicts(run, judge_model, merged)
    print(f"  judged {len(fresh)} of {len(records)} answers")
    return {
        "judge": judge_model,
        "judged": len(fresh),
        "of": len(records),
        "judge_tokens": tokens,
    }
