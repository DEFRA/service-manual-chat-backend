"""Ask every golden set question, exactly as production would.

The agent is the backend's own (`app.ask.bedrock`): same prompt, same pages,
same schema, same cache point. The model is config's BEDROCK_MODEL_ID. The
first question goes alone so the cache is written once; the rest run a few
at a time and read it.
"""

import asyncio
import statistics
import time

from evals.runs import Budget, write_answers

CONCURRENCY = 4


async def ask(agent, question: dict, corpus) -> dict:
    from app.ask.bedrock import user_prompt
    from app.ask.corpus import verify

    started = time.perf_counter()
    try:
        result = await agent.run(
            user_prompt(question["question"], question.get("previous_question"))
        )
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

    async def one(pass_number: int, question: dict) -> None:
        nonlocal stopped
        async with limit:
            if budget.exhausted:
                stopped = True
                return
            record = await ask(the_agent, question, corpus)
        usage = record.pop("_usage", None)
        if usage:
            budget.spend(usage)
        records.append(
            {
                "key": config.bedrock_model_id,
                "question_id": question["id"],
                "run": pass_number,
                **record,
            }
        )
        mark = (
            f"{record['seconds']}s" if record["ok"] else f"FAIL {record['error'][:90]}"
        )
        print(f"  pass {pass_number} {question['id']:8} {mark}")

    for pass_number in range(1, passes + 1):
        start = 0
        if pass_number == 1:
            await one(1, questions[0])
            start = 1
            if not records[0]["ok"] and "403" in records[0]["error"]:
                message = (
                    "Bedrock refused the first question (403). The key in "
                    "compose/secrets.env has probably expired. "
                    f"{records[0]['error'][:200]}"
                )
                raise SystemExit(message)
        await asyncio.gather(*(one(pass_number, q) for q in questions[start:]))

    records.sort(key=lambda r: (r["run"], r["question_id"]))
    write_answers(run, records)
    seconds = [r["seconds"] for r in records if r["ok"]]
    return {
        "answers": len(records),
        "failed_calls": sum(not r["ok"] for r in records),
        "median_seconds": round(statistics.median(seconds), 2) if seconds else None,
        "answer_tokens": {
            kind: sum(r.get(kind, 0) for r in records)
            for kind in (
                "input_tokens",
                "cache_read_tokens",
                "cache_write_tokens",
                "output_tokens",
            )
        },
        "stopped_at_ceiling": stopped,
    }
