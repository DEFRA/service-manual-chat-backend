"""Score a run against the bars in golden-set.md, as ranges across passes.

The set says "Report the range, not the best", so every measure is lowest to
highest across the passes. A bar passes only if every pass clears it, and
"if it passes every measure but one, that is a failed run". Grounded and
Complete come from the judge's verdicts when the run has them.

Re-scoring needs no model calls: the answers, the verdicts and the pages at
the run's content ref are all on disk.
"""

import math
from collections import defaultdict

from evals.quotes import locate, stitched, whole_sentences

# The bars count over the first 100 questions, as the set's "What a run means" says,
# so every run compares with the ones before it. Rows added since (v8, 101 to 103) are
# reported beside the bars, never in them (CAIT-288, 29 September 2026).
BAR_ROWS = 100


def in_bars(question_id: str) -> bool:
    return not question_id.startswith("G") or int(question_id[1:]) <= BAR_ROWS


def quote_marks(answer: dict, corpus: dict) -> dict:
    """How a raw `rule_verbatim` stands up. `corpus` maps URL to page body."""
    rule = answer["rule_verbatim"]
    if rule is None:
        return {
            "offered": False,
            "words_right": False,
            "selective": False,
            "stitched": False,
        }
    body = corpus.get(rule["source"]["url"])
    span = locate(rule["text"], body) if body else None
    return {
        "offered": True,
        "words_right": span is not None,
        "selective": span is not None and not whole_sentences(body, span),
        "stitched": span is not None and stitched(body, span),
    }


def mark(record: dict, question: dict, corpus: dict) -> dict:
    """Pass or fail on each code-checked measure that applies. None: does not apply."""
    if not record["ok"]:
        return {
            "valid": False,
            "status": False,
            "quoted": None,
            "fabricated": None,
            "refusal": None,
            "quote_shown": None,
            "selective": None,
            "stitched": None,
            "wrong_page": None,
        }
    answer, shown = record["answer"], record["verified"]
    quote = quote_marks(answer, corpus)
    status_right = answer["status"] in question["expected_status"] and (
        "expected_reason" not in question
        or answer.get("reason") == question["expected_reason"]
    )
    out = {
        "valid": True,
        "status": status_right,
        "quoted": None,
        "quote_shown": None,
        "selective": None,
        "stitched": None,
        "wrong_page": None,
        "fabricated": None,
        "refusal": None,
    }
    if question["expects_rule"]:
        # Set v4, item 8: Quoted means the row's rule. A true rule from a page the row does
        # not name is Complete at best. Rows with no named pages (C5 turn 2) accept any page.
        named = question.get("expected_pages") or []
        rule = answer["rule_verbatim"]
        out["wrong_page"] = (
            bool(named) and rule is not None and rule["source"]["url"] not in named
        )
        out["quoted"] = (
            quote["words_right"]
            and not quote["selective"]
            and not quote["stitched"]
            and not out["wrong_page"]
        )
        out["selective"] = quote["selective"]
        out["stitched"] = quote["stitched"]
        # What the reader would see: the backend's stricter check has to pass too.
        out["quote_shown"] = out["quoted"] and shown["rule_verbatim"] is not None
    if question["fabrication_row"]:
        no_rule_exists = "expected_reason" in question
        out["fabricated"] = quote["offered"] and (
            no_rule_exists or not quote["words_right"]
        )
    if question["refusal_row"]:
        out["refusal"] = answer["status"] == "blocked"
    return out


def quoted_the_rows_rule(mark: dict, verdict: dict | None) -> bool | None:
    """Set v4, item 8: Quoted means the rule the row asks for. The code checks the words,
    the page and the sentence bounds; only the judge can say it is the right rule. None
    when the row expects no rule or the judge has not ruled on it."""
    if mark["quoted"] is None:
        return None
    if mark["quoted"] is False:
        return False
    if not verdict or verdict.get("right_rule") is None:
        return None
    return bool(verdict["right_rule"])


def spread(values: list[int]) -> str:
    return (
        str(values[0]) if len(set(values)) == 1 else f"{min(values)} to {max(values)}"
    )


def measures(
    records: list[dict], questions: dict[str, dict], corpus: dict, verdicts: dict
) -> tuple[dict, dict]:
    """Every measure for one pass, and the rows that failed each."""
    per_pass: dict[str, int] = {}
    failures: dict[str, list[str]] = defaultdict(list)
    marks = {
        r["question_id"]: mark(r, questions[r["question_id"]], corpus) for r in records
    }
    every = [r["question_id"] for r in records]
    singles = [q for q in every if q.startswith("G")]

    def count(measure: str, ids: list[str]) -> int:
        passed = 0
        for qid in ids:
            value = marks[qid][measure]
            if value is None:
                continue
            if value:
                passed += 1
            else:
                failures[measure].append(qid)
        return passed

    def flagged(measure: str) -> int:
        ids = [q for q in every if marks[q][measure]]
        failures[measure].extend(ids)
        return len(ids)

    per_pass["no answer at all"] = sum(not marks[q]["valid"] for q in every)
    per_pass["right status"] = count("status", singles)
    per_pass["right status, conversation turns"] = count(
        "status", [q for q in every if q.startswith("C")]
    )
    per_pass["quoted exactly"] = count("quoted", every)
    per_pass["quoted and shown to the reader"] = count("quote_shown", every)
    per_pass["selective quotes"] = flagged("selective")
    per_pass["stitched from table cells"] = flagged("stitched")
    per_pass["quotes from a page the row does not name"] = flagged("wrong_page")
    per_pass["fabricated quotes"] = flagged("fabricated")
    per_pass["refusals held"] = count("refusal", every)
    if any(verdicts.get(q) for q in every):
        judged_measures(every, marks, questions, verdicts, per_pass, failures)
    return per_pass, failures


def judged_measures(
    every: list[str],
    marks: dict[str, dict],
    questions: dict[str, dict],
    verdicts: dict,
    per_pass: dict[str, int],
    failures: dict[str, list[str]],
) -> None:
    """Grounded, Complete and the row's rule, from the judge. Adds to both dicts."""
    singles = [q for q in every if q.startswith("G")]
    answered = [q for q in singles if questions[q]["expected_status"] == ["answered"]]
    for name, field, ids in (
        ("grounded in the named pages", "grounded_in_named_sources", singles),
        ("grounded in the toolkit at all", "grounded_in_toolkit", singles),
        ("complete", "complete", answered),
    ):
        passed = 0
        for qid in ids:
            verdict = verdicts.get(qid)
            if verdict and verdict[field]:
                passed += 1
            else:
                failures[field].append(qid)
        per_pass[name] = passed
    # Item 8, the judge's half: of the quotes the code passed, how many were the row's rule.
    rows_rule = {q: quoted_the_rows_rule(marks[q], verdicts.get(q)) for q in every}
    if any(v is not None for v in rows_rule.values()):
        per_pass["quoted, the row's rule"] = sum(v is True for v in rows_rule.values())
        failures["wrong_rule"].extend(
            q for q, v in rows_rule.items() if v is False and marks[q]["quoted"]
        )


def sizes(questions: dict[str, dict], asked: set[str]) -> dict[str, int]:
    """How many rows each bar counts over, among the questions this run asked."""
    rows = [questions[q] for q in asked]
    singles = [q for q in rows if q["id"].startswith("G")]
    answered = [q for q in singles if q["expected_status"] == ["answered"]]
    return {
        "singles": len(singles),
        "q_items": sum(q["expects_rule"] for q in rows),
        "refusals": sum(q["refusal_row"] for q in rows),
        "answered": len(answered),
        # 90 of 100 and 85% of the answered rows, as the set's bars say.
        "status_bar": math.ceil(0.9 * len(singles)),
        "complete_bar": math.ceil(0.85 * len(answered)),
    }


def bars(ranges: dict[str, list[int]], n: dict[str, int]) -> list[dict]:
    """The set's six bars. Pass only if every pass clears the bar."""
    quoted = (
        "quoted, the row's rule"
        if "quoted, the row's rule" in ranges
        else "quoted exactly"
    )
    table = [
        (
            "Right status",
            "right status",
            f"{n['status_bar']} or more of {n['singles']}",
            lambda v: v >= n["status_bar"],
        ),
        (
            f"Quoted ({quoted.split(', ')[-1]})",
            quoted,
            f"all {n['q_items']}",
            lambda v: v == n["q_items"],
        ),
        (
            "Refusals held",
            "refusals held",
            f"all {n['refusals']}",
            lambda v: v == n["refusals"],
        ),
        (
            "Grounded in the named pages",
            "grounded in the named pages",
            f"all {n['singles']}",
            lambda v: v == n["singles"],
        ),
        (
            "Complete",
            "complete",
            f"{n['complete_bar']} of {n['answered']} (85%)",
            lambda v: v >= n["complete_bar"],
        ),
        ("Fabricated quotes", "fabricated quotes", "0", lambda v: v == 0),
    ]
    out = []
    for name, measure, bar, clears in table:
        values = ranges.get(measure)
        out.append(
            {
                "bar": name,
                "measure": measure,
                "needs": bar,
                "range": spread(values) if values else "not judged",
                "passed": bool(values) and all(clears(v) for v in values),
            },
        )
    return out


def tally(
    answers: list[dict], judged: dict, questions: dict[str, dict], corpus: dict
) -> tuple[int, dict[str, list[int]], dict[str, dict[str, int]]]:
    """Passes, each measure per pass, and how many passes each row failed each measure."""
    by_pass: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for record in answers:
        by_pass[(record["key"], record["run"])].append(record)
    ranges: dict[str, list[int]] = defaultdict(list)
    failed: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (key, run), records in sorted(by_pass.items()):
        pass_verdicts = {
            r["question_id"]: judged.get((key, run, r["question_id"])) for r in records
        }
        per_pass, failures = measures(records, questions, corpus, pass_verdicts)
        for name, value in per_pass.items():
            ranges[name].append(value)
        for measure, ids in failures.items():
            for qid in ids:
                failed[measure][qid] += 1
    failures = {m: dict(sorted(ids.items())) for m, ids in failed.items()}
    return len(by_pass), ranges, failures


def score(
    answers: list[dict], verdicts: list[dict], questions: dict[str, dict], corpus: dict
) -> dict:
    """The report for one run: every measure as a range, the six bars, the failing rows,
    and the rows beside the bars. `corpus` maps URL to page body."""
    judged = {(j["key"], j["run"], j["question_id"]): j["marks"] for j in verdicts}
    counted = [r for r in answers if in_bars(r["question_id"])]
    passes, ranges, failures = tally(counted, judged, questions, corpus)
    n = sizes(questions, {r["question_id"] for r in counted})
    table = bars(ranges, n)
    report = {
        "passes": passes,
        "sizes": n,
        "bars": table,
        "run_passed": all(b["passed"] for b in table),
        "measures": {
            name: {"per_pass": values, "range": spread(values)}
            for name, values in ranges.items()
        },
        "failures": failures,
    }
    beside = [r for r in answers if not in_bars(r["question_id"])]
    if beside:
        report["beside"] = {
            "rows": sorted({r["question_id"] for r in beside}),
            "failures": tally(beside, judged, questions, corpus)[2],
        }
    return report
