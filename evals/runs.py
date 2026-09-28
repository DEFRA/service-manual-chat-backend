"""One directory per run under evals/results, holding everything needed to
re-score it or compare it with another run:

    meta.json          what was run: set, prompt, content ref, model, date
    answers.jsonl.gz   one line per question per pass, the full answer
    verdicts.json.gz   the judge's Grounded, Complete and right rule verdicts
    report.json        the bars, as ranges across the passes
"""

import gzip
import json
import time
from pathlib import Path

from evals.setup import RESULTS

META = "meta.json"
ANSWERS = "answers.jsonl.gz"
VERDICTS = "verdicts.json.gz"
REPORT = "report.json"


class Budget:
    """Stops a run at a token ceiling, answers and judge together."""

    def __init__(self, ceiling: int) -> None:
        self.ceiling = ceiling
        self.spent = 0

    def spend(self, usage) -> None:
        self.spent += usage.input_tokens + usage.output_tokens

    @property
    def exhausted(self) -> bool:
        return self.spent >= self.ceiling


def new_run(label: str = "") -> Path:
    name = time.strftime("%Y%m%dT%H%M%S")
    if label:
        name += "-" + "".join(c if c.isalnum() or c in "-_" else "-" for c in label)
    path = RESULTS / name
    path.mkdir(parents=True)
    return path


def read_meta(run: Path) -> dict:
    return json.loads((run / META).read_text(encoding="utf-8"))


def write_meta(run: Path, **fields) -> dict:
    meta = read_meta(run) if (run / META).exists() else {}
    meta.update(fields)
    (run / META).write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return meta


def read_answers(run: Path) -> list[dict]:
    with gzip.open(run / ANSWERS, "rt", encoding="utf-8") as lines:
        return [json.loads(line) for line in lines]


def write_answers(run: Path, records: list[dict]) -> None:
    with gzip.open(run / ANSWERS, "wt", encoding="utf-8") as out:
        out.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in records)


def read_verdicts(run: Path) -> list[dict]:
    if not (run / VERDICTS).exists():
        return []
    with gzip.open(run / VERDICTS, "rt", encoding="utf-8") as source:
        return json.load(source)["judged"]


def write_verdicts(run: Path, judge: str, judged: list[dict]) -> None:
    with gzip.open(run / VERDICTS, "wt", encoding="utf-8") as out:
        json.dump({"judge": judge, "judged": judged}, out, indent=1, ensure_ascii=False)
