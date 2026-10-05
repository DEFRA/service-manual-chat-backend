"""Turn evals/golden-set.md into evals/golden-set.json.

    uv run python -m evals golden

golden-set.md is synced from the team's golden set page on Confluence and is
never edited here. Questions and expected answers are copied as written,
never retyped: the set says "Do not change a question because the service
fails it."

Conversations: every conversation is asked turn by turn, as a reader would,
and each later turn is scored. A turn row carries the questions before it
as `earlier`; the answers to those are whatever the service really gave,
which the run asks for live (CAIT-290). Turn 1 is asked and not scored.
"""

import hashlib
import json
import re

from evals.setup import EVALS

GOLDEN_MD = EVALS / "golden-set.md"
GOLDEN_JSON = EVALS / "golden-set.json"

STATUSES = (
    "answered",
    "need_more_detail",
    "cannot_answer",
    "talk_to_a_person",
    "blocked",
)
FABRICATION_ROWS = range(71, 77)
REFUSAL_ROWS = range(92, 96)

# C15 is "Four unrelated questions in sequence", which the set does not write
# out. These are the first rows of sections 1 to 4, taken from the set as
# written, so nothing here is a question of our own.
C15_ROWS = (1, 19, 31, 41)
C15_LAST = "then:"
TURN = " → "


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_status(cell: str) -> tuple[str, str | None, bool]:
    found = re.findall(r"`([a-z_]+)`", cell)
    status = next(s for s in found if s in STATUSES)
    reason = next(
        (s for s in found if s in ("outside_toolkit", "no_guidance_yet")), None
    )
    return status, reason, "**Q**" in cell


def pages_for(cell: str, titles: dict[str, str]) -> list[str]:
    if cell.strip().lower() == "none":
        return []
    # The set writes "Model Context Protocol"; the page is titled with "(MCP)".
    return [
        next(
            url
            for title, url in titles.items()
            if title == name.strip() or title.startswith(name.strip() + " (")
        )
        for name in cell.split(",")
    ]


def version(markdown: str) -> str:
    """The set's version, from its Status row: "Draft v6, for review" is v6."""
    match = re.search(r"^\| \*\*Status\*\* \|[^|]*\b(v\d+)\b", markdown, re.MULTILINE)
    if not match:
        message = "no version in the Status row of golden-set.md"
        raise SystemExit(message)
    return match.group(1)


def single(row: list[str], section: str, titles: dict[str, str]) -> dict:
    number = int(row[0])
    status, reason, quoted = parse_status(row[2])
    question = {
        "id": f"G{number:03}",
        "section": section,
        "question": row[1],
        "expected_status": [status],
        "expected_answer": row[3],
        "expects_rule": quoted,
        "fabrication_row": number in FABRICATION_ROWS,
        "refusal_row": number in REFUSAL_ROWS,
    }
    if reason:
        question["expected_reason"] = reason
    if len(row) == 5:  # sections 1 to 7 name their source pages
        question["expected_pages"] = pages_for(row[4], titles)
    return question


def turn_statuses(cell: str, turns: int) -> list[list[str]]:
    """What each turn after the first should come back as."""
    found = [s for s in re.findall(r"`([a-z_]+)`", cell) if s in STATUSES]
    # A longer conversation lists a status for each turn, turn 1 first. A pair
    # names the later turn's status first, whatever else the cell says:
    # "`blocked`, after an `answered` turn 1".
    if turns > 2 and len(found) == turns:
        return [[status] for status in found[1:]]
    return [[found[0]]] * (turns - 1)


def conversation(row: list[str], singles: dict[int, str]) -> list[dict]:
    """A row for each turn after the first, with the questions before it."""
    name, first, then, expected = row[:4]
    if C15_LAST in first:
        asked = [singles[n] for n in C15_ROWS] + [first.split(C15_LAST)[1].strip()]
        statuses = {len(asked): ["answered", "cannot_answer"]}
    else:
        asked = first.split(TURN) if TURN in first else [first, then]
        statuses = dict(
            enumerate(turn_statuses(expected, len(asked)), start=2),
        )
    quoted = "**Q**" in expected
    return [
        {
            "id": f"{name}-t{turn}",
            "section": "Conversations",
            "earlier": asked[: turn - 1],
            "question": asked[turn - 1],
            "expected_status": status,
            "expected_answer": expected,
            "expects_rule": quoted,
            "fabrication_row": False,
            "refusal_row": status == ["blocked"],
        }
        for turn, status in statuses.items()
    ]


def parse(markdown: str, titles: dict[str, str]) -> dict:
    questions, section = [], ""
    singles: dict[int, str] = {}
    for line in markdown.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        if not line.startswith("|"):
            continue
        row = cells(line)
        if re.fullmatch(r"\d+", row[0]):
            questions.append(single(row, section, titles))
            singles[int(row[0])] = row[1]
        elif re.fullmatch(r"C\d+", row[0]):
            questions.extend(conversation(row, singles))
    return {
        "version": version(markdown),
        "source_sha": hashlib.sha256(markdown.encode("utf-8")).hexdigest()[:12],
        "note": "Generated by `python -m evals golden` from golden-set.md. Do not edit.",
        "not_run": {},
        "questions": questions,
    }


def load() -> dict:
    return json.loads(GOLDEN_JSON.read_text(encoding="utf-8"))


def main() -> None:
    from evals.setup import content, prepare

    content_dir, _ = content()
    prepare(content_dir, needs_bedrock=False)
    from app.ask.corpus import load_corpus

    titles = {page.title: url for url, page in load_corpus(content_dir).items()}
    data = parse(GOLDEN_MD.read_text(encoding="utf-8"), titles)
    GOLDEN_JSON.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    singles = sum(q["id"].startswith("G") for q in data["questions"])
    print(
        f"Golden set {data['version']}: {singles} questions and "
        f"{len(data['questions']) - singles} conversation turns written to {GOLDEN_JSON.name}",
    )
