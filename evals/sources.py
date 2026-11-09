"""Count missing source lists in saved answers, without re-verifying or model calls."""

import argparse
import json
import re
from pathlib import Path

from evals import runs


def question_type(question_id: str) -> str:
    """Use turn IDs, not history: blocked turns can leave history empty."""
    if re.fullmatch(r"G\d+", question_id):
        return "first_question"
    conversation = re.fullmatch(r"C\d+-t([1-9]\d*)", question_id)
    if conversation:
        return "first_question" if int(conversation[1]) == 1 else "follow_up"
    message = f"Unrecognised evaluation question ID: {question_id}"
    raise ValueError(message)


def count(records: list[dict]) -> dict:
    groups: dict[str, dict] = {
        kind: {
            "answered": 0,
            "no_sources": 0,
            "no_sources_cases": [],
            "quoted_page_missing": 0,
            "quoted_page_missing_cases": [],
        }
        for kind in ("first_question", "follow_up")
    }
    failed_calls = 0
    other_statuses = 0
    for record in records:
        if not record["ok"]:
            failed_calls += 1
            continue
        shown = record["verified"]
        if shown["status"] != "answered":
            other_statuses += 1
            continue
        group = groups[question_type(record["question_id"])]
        group["answered"] += 1
        case = {
            "question_id": record["question_id"],
            "key": record["key"],
            "pass": record["run"],
        }
        sources = shown["sources"]
        if not isinstance(sources, list):
            message = f"Expected a saved source list: {case}"
            raise ValueError(message)
        if not sources:
            group["no_sources"] += 1
            group["no_sources_cases"].append(case)
        rule = shown["rule_verbatim"]
        if rule is not None and rule["source"]["url"] not in {
            source["url"] for source in sources
        }:
            group["quoted_page_missing"] += 1
            group["quoted_page_missing_cases"].append(case)

    for group in groups.values():
        group["no_sources_percent"] = (
            round(100 * group["no_sources"] / group["answered"], 2)
            if group["answered"]
            else None
        )
    return {
        "groups": groups,
        "excluded_failed_calls": failed_calls,
        "excluded_other_statuses": other_statuses,
    }


def report(run: Path) -> dict:
    meta = runs.read_meta(run)
    return {
        "run": run.name,
        "date": meta["date"],
        "questions": meta.get("questions"),
        "passes": meta["passes"],
        "prompt": meta["prompt"],
        "content_ref": meta["content_ref"],
        "unscored_turns_not_persisted": meta.get("unscored_turns"),
        **count(runs.read_answers(run)),
    }


def command(args: argparse.Namespace) -> None:
    print(json.dumps([report(run) for run in args.runs], indent=2))
