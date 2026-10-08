"""The golden set evaluation, one command per job.

uv run run-evals run --label cait-288-step-2     # ask x3, judge, score
uv run run-evals score evals/results/<run>       # re-score, no model calls
uv run run-evals judge evals/results/<run> [--judge ID] [--questions Q --only right_rule]
uv run run-evals golden                          # golden-set.md -> golden-set.json
uv run run-evals agree <run> <run>               # two judges' verdicts side by side
uv run run-evals import <old>.jsonl ...          # bring in a prototype run
"""

import argparse
import asyncio
import datetime
import json
import pathlib
import typing

from evals import golden, runs, setup

DEFAULT_CEILING = 30_000_000
TOKEN_KINDS = (
    "input_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "output_tokens",
)


def pick_questions(
    set_data: dict[str, typing.Any], ids: str | None
) -> list[dict[str, typing.Any]]:
    questions: list[dict[str, typing.Any]] = set_data["questions"]
    if ids == "Q":
        return [q for q in questions if q["expects_rule"]]
    if ids:
        return [q for q in questions if q["id"] in ids.split(",")]
    return questions


def pounds(tokens: dict[str, typing.Any], model_id: str) -> float | None:
    """What those tokens cost at the dated London prices. Input tokens include cache reads
    and writes, so those are taken out and priced at their own rates."""
    prices: dict[str, typing.Any] = json.loads(
        (setup.EVALS / "prices.json").read_text(encoding="utf-8")
    )
    price = prices["models"].get(model_id)
    if not price or not tokens:
        return None
    cached = tokens["cache_read_tokens"] + tokens["cache_write_tokens"]
    usd = (
        (tokens["input_tokens"] - cached) * price["input"]
        + tokens["cache_read_tokens"] * price["cache_read"]
        + tokens["cache_write_tokens"] * price["cache_write"]
        + tokens["output_tokens"] * price["output"]
    ) / 1_000_000
    return float(round(usd * prices["usd_to_gbp"], 2))


def rescore(
    run: pathlib.Path, set_path: pathlib.Path | None, content_dir: pathlib.Path | None
) -> dict[str, typing.Any]:
    meta = runs.read_meta(run)
    set_data = (
        json.loads(set_path.read_text(encoding="utf-8")) if set_path else golden.load()
    )
    if set_data["version"] != meta["golden_set"]:
        print(
            f"Warning: this run used golden set {meta['golden_set']}, scoring against {set_data['version']}. "
            "Pass --set with the matching golden-set.json to reproduce its figures.",
        )
    local = meta["content_ref"].startswith("local")
    if local and not content_dir:
        message = f"This run answered from a local checkout ({meta['content_ref']}). Pass --content-dir."
        raise SystemExit(message)
    pages, _ = setup.content(content_dir, None if local else meta["content_ref"])
    setup.prepare(pages, needs_bedrock=False)
    from app.ask import corpus as app_corpus
    from evals import score as scoring
    from evals import writing

    corpus = {url: page.body for url, page in app_corpus.load_corpus(pages).items()}
    questions = {q["id"]: q for q in set_data["questions"]}
    answers = runs.read_answers(run)
    report = scoring.score(answers, runs.read_verdicts(run), questions, corpus)
    report["writing"] = writing.counts(answers)
    (run / runs.REPORT).write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def show(run: pathlib.Path, report: dict[str, typing.Any]) -> None:
    meta = runs.read_meta(run)
    answer_cost = pounds(meta.get("answer_tokens", {}), meta["model_id"])
    judge_cost = pounds(meta.get("judge_tokens", {}), meta.get("judge", ""))
    lines = [
        f"Run            {run.relative_to(setup.REPO)}",
        f"Date           {meta['date']}",
        f"Label          {meta.get('label') or '-'}",
        f"Golden set     {meta['golden_set']}",
        f"Prompt         {meta['prompt']}",
        f"Content ref    {meta['content_ref']}",
        f"Model          {meta['model_id']}",
        f"Judge          {meta.get('judge', 'not judged')}",
        f"Passes         {report['passes']}",
        "",
    ]
    width = max(len(b["bar"]) for b in report["bars"])
    for b in report["bars"]:
        lines.append(
            f"{b['bar']:<{width}}  {b['range']:>12}  needs {b['needs']:<18} {'pass' if b['passed'] else 'FAIL'}"
        )
    failed = sum(not b["passed"] for b in report["bars"])
    verdict = (
        "PASSED"
        if report["run_passed"]
        else f"FAILED, {failed} of {len(report['bars'])} bars"
    )
    lines += ["", f"Run            {verdict}"]
    if meta.get("median_seconds") is not None:
        lines.append(f"Median answer  {meta['median_seconds']} seconds")
    costs = [c for c in (answer_cost, judge_cost) if c is not None]
    if costs:
        lines.append(
            f"Cost           £{sum(costs):.2f} (answers £{answer_cost or 0:.2f}, judge £{judge_cost or 0:.2f})"
        )
    if meta.get("stopped_at_ceiling"):
        lines.append(
            f"Stopped        at the token ceiling of {meta['token_ceiling']:,}; the figures are partial"
        )
    lines += ["", "Other measures, lowest to highest across passes:"]
    shown = {b["measure"] for b in report["bars"]}
    lines += [
        f"  {name:44} {m['range']}"
        for name, m in report["measures"].items()
        if name not in shown
    ]
    lines += ["", "Writing, messages across all passes:"]
    lines += [f"  {name:44} {value}" for name, value in report["writing"].items()]
    lines += ["", "Rows failing a bar (row x passes):"]
    lines += failing(report["failures"])
    beside = report.get("beside")
    if beside:
        rows = beside["rows"]
        lines += ["", f"Rows beside the bars, {', '.join(rows)} (row x passes):"]
        lines += failing(beside["failures"]) or ["  none failed"]
    first = report.get("first_turns")
    if first:
        lines += ["", f"Turn 1 of {first['checked']} conversations, status only:"]
        lines += [
            f"  {name}: " + ", ".join(f"{status}x{n}" for status, n in got.items())
            for name, got in first["failures"].items()
        ] or ["  all as expected"]
    print("\n".join(lines))


def failing(failures: dict[str, dict[str, int]]) -> list[str]:
    lines = []
    for measure in (
        "status",
        "quoted",
        "wrong_rule",
        "grounded_in_named_sources",
        "complete",
        "complete_conversation",
        "refusal",
        "fabricated",
    ):
        rows = failures.get(measure)
        if rows:
            lines.append(
                f"  {measure}: " + ", ".join(f"{q}x{n}" for q, n in rows.items())
            )
    return lines


async def run_all(args: argparse.Namespace) -> pathlib.Path:
    set_data = golden.load()
    questions = pick_questions(set_data, args.questions)
    pages, ref = setup.content(args.content_dir)
    setup.prepare(pages, needs_bedrock=True)
    from app import config as app_config
    from evals import answer as answering
    from evals import judge as judging

    config = app_config.config

    run = runs.new_run(args.label)
    runs.write_meta(
        run,
        date=datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        label=args.label,
        golden_set=set_data["version"],
        golden_set_sha=set_data["source_sha"],
        questions=args.questions or "all",
        prompt=setup.prompt_version(),
        content_ref=ref,
        model_id=config.bedrock_model_id,
        passes=args.passes,
        token_ceiling=args.max_tokens,
    )
    budget = runs.Budget(args.max_tokens)
    print(
        f"{len(questions)} questions x {args.passes} passes on {config.bedrock_model_id}, into {run.relative_to(setup.REPO)}"
    )
    runs.write_meta(run, **await answering.answer(run, questions, args.passes, budget))
    if not args.no_judge:
        print(f"Judging with {judging.JUDGE_MODEL_ID}")
        by_id = {q["id"]: q for q in set_data["questions"]}
        summary = await judging.judge(run, by_id, budget)
        runs.write_meta(run, **summary)
    runs.write_meta(run, stopped_at_ceiling=budget.exhausted, tokens_spent=budget.spent)
    return run


async def judge_again(args: argparse.Namespace) -> None:
    meta = runs.read_meta(args.run)
    pages, _ = setup.content(
        args.content_dir,
        None if meta["content_ref"].startswith("local") else meta["content_ref"],
    )
    setup.prepare(pages, needs_bedrock=True)
    from evals import judge as judging

    set_data = golden.load()
    ids = (
        [q["id"] for q in pick_questions(set_data, args.questions)]
        if args.questions
        else None
    )
    summary = await judging.judge(
        args.run,
        {q["id"]: q for q in set_data["questions"]},
        runs.Budget(args.max_tokens),
        judge_model=args.judge,
        only_questions=ids,
        only_fields=args.only.split(",") if args.only else None,
    )
    if not args.only and not args.questions:
        runs.write_meta(args.run, **summary)


def import_run(args: argparse.Namespace) -> None:
    """A run from the harness used before this one (golden-*.jsonl, one line per answer) as a run directory."""
    records = [
        json.loads(line) for line in args.jsonl.read_text(encoding="utf-8").splitlines()
    ]
    records = [r for r in records if r.get("caching") != "refused"]
    run = setup.RESULTS / f"{args.jsonl.stem.removeprefix('golden-')}-imported"
    run.mkdir(parents=True)
    runs.write_answers(run, records)
    judged = args.jsonl.with_suffix(".judged.json")
    if judged.exists():
        data = json.loads(judged.read_text(encoding="utf-8"))
        runs.write_verdicts(run, data["judge"], data["judged"])
    stamp = args.jsonl.stem.removeprefix("golden-")[:15]
    runs.write_meta(
        run,
        date=datetime.datetime.strptime(stamp, "%Y%m%dT%H%M%S")
        .replace(tzinfo=datetime.UTC)
        .isoformat(),
        label=args.label or records[0].get("label", ""),
        golden_set=args.golden_set,
        prompt=records[0].get("prompt_sha") or "not recorded",
        content_ref=args.content_ref,
        model_id=records[0]["model_id"],
        passes=len({r["run"] for r in records}),
        judge=json.loads(judged.read_text(encoding="utf-8"))["judge"]
        if judged.exists()
        else "not judged",
        imported_from=args.jsonl.name,
    )
    print(f"Imported {len(records)} answers into {run.relative_to(setup.REPO)}")


def run_command(args: argparse.Namespace) -> None:
    path = asyncio.run(run_all(args))
    show(path, rescore(path, None, args.content_dir))


def score_command(args: argparse.Namespace) -> None:
    for path in args.runs:
        show(path, rescore(path, args.set, args.content_dir))
        print()


def agree(args: argparse.Namespace) -> None:
    fields = (
        "grounded_in_named_sources",
        "grounded_in_toolkit",
        "complete",
        "right_rule",
    )
    passes = [
        {
            (j["key"], j["run"], j["question_id"]): j["marks"]
            for j in runs.read_verdicts(run)
        }
        for run in args.runs
    ]
    keys = set.intersection(*(set(p) for p in passes))
    print(f"{len(passes)} sets of verdicts, {len(keys)} answers judged by all\n")
    for field in fields:
        values = {k: [p[k].get(field) for p in passes] for k in keys}
        values = {k: v for k, v in values.items() if all(x is not None for x in v)}
        same = sum(len(set(v)) == 1 for v in values.values())
        print(f"{field}: all agree on {same} of {len(values)}")
        for (_, run, qid), v in sorted(
            values.items(), key=lambda kv: (kv[0][2], kv[0][1])
        ):
            if len(set(v)) > 1:
                print(f"    {qid} pass {run}: " + "".join("P" if x else "F" for x in v))


def resolved(value: str) -> pathlib.Path:
    return pathlib.Path(value).resolve()


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(
        prog="run-evals", description=(__doc__ or "").splitlines()[0]
    )
    commands = top.add_subparsers(dest="command", required=True)

    run = commands.add_parser(
        "run", help="ask every question, judge, score, print the bars"
    )
    run.set_defaults(handler=run_command)
    run.add_argument("--passes", type=int, default=3)
    run.add_argument(
        "--label", default="", help="what this run tests, e.g. cait-288-step-2"
    )
    run.add_argument(
        "--questions", help="comma-separated ids, or Q for the quote rows; default all"
    )
    run.add_argument(
        "--content-dir",
        type=resolved,
        help="a local service-manual-ui src/content; default the Dockerfile's ref",
    )
    run.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_CEILING,
        help="stop at this many tokens, answers and judge",
    )
    run.add_argument(
        "--no-judge",
        action="store_true",
        help="code-checked bars only; Grounded and Complete not judged",
    )

    score_cmd = commands.add_parser(
        "score", help="re-score runs from disk, no model calls"
    )
    score_cmd.set_defaults(handler=score_command)
    score_cmd.add_argument("runs", nargs="+", type=resolved)
    score_cmd.add_argument(
        "--set", type=resolved, help="a golden-set.json other than the current one"
    )
    score_cmd.add_argument("--content-dir", type=resolved)

    judge_cmd = commands.add_parser("judge", help="judge, or re-judge, a run's answers")
    judge_cmd.set_defaults(handler=lambda args: asyncio.run(judge_again(args)))
    judge_cmd.add_argument("run", type=resolved)
    judge_cmd.add_argument("--judge", default="anthropic.claude-opus-4-6-v1")
    judge_cmd.add_argument("--questions", help="comma-separated ids, or Q")
    judge_cmd.add_argument(
        "--only", help="take only these verdicts from the re-judge, e.g. right_rule"
    )
    judge_cmd.add_argument("--content-dir", type=resolved)
    judge_cmd.add_argument("--max-tokens", type=int, default=DEFAULT_CEILING)

    golden_cmd = commands.add_parser(
        "golden", help="regenerate golden-set.json from golden-set.md"
    )
    golden_cmd.set_defaults(handler=lambda _: golden.main())

    agree_cmd = commands.add_parser(
        "agree", help="compare the verdicts of two or more runs of the same answers"
    )
    agree_cmd.set_defaults(handler=agree)
    agree_cmd.add_argument("runs", nargs="+", type=resolved)

    import_cmd = commands.add_parser(
        "import", help="bring in a run from the earlier harness"
    )
    import_cmd.set_defaults(handler=import_run)
    import_cmd.add_argument("jsonl", type=resolved)
    import_cmd.add_argument(
        "--golden-set", required=True, help="the set version it ran, e.g. v3"
    )
    import_cmd.add_argument(
        "--content-ref",
        required=True,
        help="the service-manual-ui commit it answered from",
    )
    import_cmd.add_argument("--label", default="")
    return top


def main() -> None:
    args = parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
