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
import statistics
import time

from evals.runs import Budget, write_answers

CONCURRENCY = 4


async def ask(agent, question: str, history: list, corpus) -> dict:
    from app.ask.bedrock import user_prompt
    from app.ask.corpus import verify

    started = time.perf_counter()
    try:
        result = await agent.run(user_prompt(question, history))
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
        "verified": verify(result.output, corpus).model_dump(),
        "_usage": usage,
    }


def units(questions: list[dict]) -> list[list[dict]]:
    """Each single question on its own, and a conversation's turns together."""
    grouped: dict[str, list[dict]] = {}
    for question in questions:
        grouped.setdefault(question["id"].split("-t")[0], []).append(question)
    return list(grouped.values())


def as_sent(seen: list) -> list:
    """The turns the front end would send: no blocked ones, and the last few."""
    from app.ask.schemas import MAX_HISTORY_TURNS

    return [turn for turn in seen if turn.status != "blocked"][-MAX_HISTORY_TURNS:]


def as_turn(question: str, shown: dict):
    """One exchange as the reader saw it, in the shape `/ask` takes as history."""
    from app.ask.schemas import MAX_MESSAGE_LENGTH, Turn

    return Turn(
        question=question,
        status=shown["status"],
        message=shown["message"][:MAX_MESSAGE_LENGTH],
        options=shown["options"],
    )


async def ask_unit(rows: list[dict], call) -> tuple[list[dict], list[dict]]:
    """Ask a single question, or a conversation from its first turn.

    `call(question, history)` gives one record, or None once the run has
    reached its ceiling. Returns a record for each row, and the records of
    the turns that were asked only to get to them.
    """
    last = rows[-1]
    asked = [*last.get("earlier", []), last["question"]]
    scored = {len(row.get("earlier", [])) + 1: row for row in rows}
    records: list[dict] = []
    unscored: list[dict] = []
    seen: list = []
    lost_at = None
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
        except (KeyError, ValueError):
            # No answer, or one `/ask` would refuse as history: the
            # conversation cannot go on, in the evaluation or for a reader.
            lost_at = number
    return records, unscored


async def answer(run, questions: list[dict], passes: int, budget: Budget) -> dict:
    """Ask every question `passes` times. Returns a summary for meta.json."""
    from pathlib import Path

    from app.ask.bedrock import agent
    from app.ask.corpus import load_corpus
    from app.config import config

    corpus = load_corpus(Path(config.content_dir))
    the_agent = agent()
    limit = asyncio.Semaphore(CONCURRENCY)
    records: list[dict] = []
    stopped = False

    unscored: list[dict] = []

    async def call(question: str, history: list) -> dict | None:
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

    async def one(pass_number: int, unit: list[dict]) -> None:
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
                    "compose/secrets.env has probably expired. "
                    f"{first['error'][:200]}"
                )
                raise SystemExit(message)
        await asyncio.gather(*(one(pass_number, unit) for unit in every[start:]))

    records.sort(key=lambda r: (r["run"], r["question_id"]))
    write_answers(run, records)
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
