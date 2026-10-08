"""Ask every golden set question, exactly as production would.

The agent is the backend's own (`app.ask.bedrock`): same prompt, same pages,
same schema, same cache point. The model is config's BEDROCK_MODEL_ID. The
first question goes alone so the cache is written once; the rest run a few
at a time and read it.

A conversation is asked turn by turn. Each turn is sent the answers the
service really gave to the turns before it, cut and filtered as the front
end does, so a run cannot pass while the service has lost the thread
(CAIT-290). Turn 1 is asked to get there and is not scored.
"""

import asyncio
import collections.abc
import pathlib
import statistics
import time
import typing

import pydantic_ai

from evals import runs

if typing.TYPE_CHECKING:
    from app.ask import schemas as app_schemas

CONCURRENCY = 4

# Asks one question given the conversation so far; None once the run has reached
# its ceiling.
Caller = collections.abc.Callable[
    [str, list["app_schemas.Turn"]],
    collections.abc.Awaitable[dict[str, typing.Any] | None],
]


async def ask(
    agent: pydantic_ai.Agent[typing.Any, typing.Any],
    question: str,
    history: list[app_schemas.Turn],
    corpus: dict[str, typing.Any],
) -> dict[str, typing.Any]:
    from app.ask import bedrock
    from app.ask import corpus as app_corpus

    started = time.perf_counter()
    try:
        result = await agent.run(bedrock.user_prompt(question, history))
    except Exception as error:  # noqa: BLE001 - every failure is a finding
        return {
            "ok": False,
            "seconds": round(time.perf_counter() - started, 2),
            "error": f"{type(error).__name__}: {str(error)[:500]}",
        }
    usage = result.usage
    return {
        "ok": True,
        "seconds": round(time.perf_counter() - started, 2),
        "requests": usage.requests,
        "input_tokens": usage.input_tokens,
        "cache_write_tokens": usage.cache_write_tokens,
        "cache_read_tokens": usage.cache_read_tokens,
        "output_tokens": usage.output_tokens,
        "answer": result.output.model_dump(),
        "verified": app_corpus.verify(result.output, corpus).model_dump(),
        "_usage": usage,
    }


def units(questions: list[dict[str, typing.Any]]) -> list[list[dict[str, typing.Any]]]:
    """Each single question on its own, and a conversation's turns together."""
    grouped: dict[str, list[dict[str, typing.Any]]] = {}
    for question in questions:
        grouped.setdefault(question["id"].split("-t")[0], []).append(question)
    return list(grouped.values())


def as_sent(seen: list[app_schemas.Turn]) -> list[app_schemas.Turn]:
    """The turns the front end would send: no blocked ones, and the last few."""
    from app.ask import schemas

    return [turn for turn in seen if turn.status != "blocked"][
        -schemas.MAX_HISTORY_TURNS :
    ]


def as_turn(question: str, shown: dict[str, typing.Any]) -> app_schemas.Turn:
    """One exchange as the reader saw it, in the shape `/ask` takes as history."""
    from app.ask import schemas

    return schemas.Turn(
        question=question,
        status=shown["status"],
        message=shown["message"][: schemas.MAX_MESSAGE_LENGTH],
        options=shown["options"],
    )


async def ask_unit(
    rows: list[dict[str, typing.Any]], call: Caller
) -> tuple[list[dict[str, typing.Any]], list[dict[str, typing.Any]]]:
    """Ask a single question, or a conversation from its first turn.

    `call(question, history)` gives one record, or None once the run has
    reached its ceiling. Returns a record for each row, and the records of
    the turns that were asked only to get to them.
    """
    last = rows[-1]
    asked = [*last.get("earlier", []), last["question"]]
    scored = {len(row.get("earlier", [])) + 1: row for row in rows}
    records: list[dict[str, typing.Any]] = []
    unscored: list[dict[str, typing.Any]] = []
    seen: list[app_schemas.Turn] = []
    lost_at: int | None = None
    for number, question in enumerate(asked, start=1):
        row = scored.get(number)
        if lost_at:
            if row:
                records.append(
                    {
                        "question_id": row["id"],
                        "ok": False,
                        "seconds": 0,
                        "error": f"turn {lost_at} gave no answer to carry "
                        "forward, so this turn was not asked",
                    }
                )
            continue
        history = as_sent(seen)
        record = await call(question, history)
        if record is None:
            break
        if row:
            sent = {"history": [turn.model_dump() for turn in history]}
            records.append(
                {"question_id": row["id"], **record, **(sent if history else {})}
            )
        else:
            unscored.append(record)
        try:
            seen.append(as_turn(question, record["verified"]))
        except KeyError, ValueError:
            # No answer, or one `/ask` would refuse as history: the
            # conversation cannot go on, in the evaluation or for a reader.
            lost_at = number
    return records, unscored


async def answer(
    run: pathlib.Path,
    questions: list[dict[str, typing.Any]],
    passes: int,
    budget: runs.Budget,
) -> dict[str, typing.Any]:
    """Ask every question `passes` times. Returns a summary for meta.json."""
    from app import config as app_config
    from app.ask import bedrock
    from app.ask import corpus as app_corpus

    config = app_config.config
    corpus = app_corpus.load_corpus(pathlib.Path(config.content_dir))
    the_agent = bedrock.agent()
    limit = asyncio.Semaphore(CONCURRENCY)
    records: list[dict[str, typing.Any]] = []
    stopped = False

    unscored: list[dict[str, typing.Any]] = []

    async def call(
        question: str, history: list[app_schemas.Turn]
    ) -> dict[str, typing.Any] | None:
        nonlocal stopped
        async with limit:
            if budget.exhausted:
                stopped = True
                return None
            record = await ask(the_agent, question, history, corpus)
        usage = record.pop("_usage", None)
        if usage:
            budget.spend(usage)
        return record

    async def one(pass_number: int, unit: list[dict[str, typing.Any]]) -> None:
        answered, setup = await ask_unit(unit, call)
        unscored.extend(setup)
        for record in answered:
            records.append(
                {"key": config.bedrock_model_id, "run": pass_number, **record}
            )
            mark = (
                f"{record['seconds']}s"
                if record["ok"]
                else f"FAIL {record['error'][:90]}"
            )
            print(f"  pass {pass_number} {record['question_id']:8} {mark}")

    every = units(questions)
    for pass_number in range(1, passes + 1):
        start = 0
        if pass_number == 1:
            await one(1, every[0])
            start = 1
            first = next(iter(records or unscored), None)
            if first and not first["ok"] and "403" in first["error"]:
                message = (
                    "Bedrock refused the first question (403). The key in "
                    ".env has probably expired. "
                    f"{first['error'][:200]}"
                )
                raise SystemExit(message)
        await asyncio.gather(*(one(pass_number, unit) for unit in every[start:]))

    records.sort(key=lambda r: (r["run"], r["question_id"]))
    runs.write_answers(run, records)
    seconds = [r["seconds"] for r in records if r["ok"]]
    return {
        "answers": len(records),
        "failed_calls": sum(not r["ok"] for r in records),
        "median_seconds": round(statistics.median(seconds), 2) if seconds else None,
        # Turn 1 of each conversation is asked and paid for, and not scored.
        "unscored_turns": len(unscored),
        "answer_tokens": {
            kind: sum(r.get(kind, 0) for r in [*records, *unscored])
            for kind in (
                "input_tokens",
                "cache_read_tokens",
                "cache_write_tokens",
                "output_tokens",
            )
        },
        "stopped_at_ceiling": stopped,
    }
