import json
from pathlib import Path

import pytest

from evals import runs, sources
from evals.__main__ import parser


def record(
    question_id: str = "G001",
    *,
    urls: tuple[str, ...] = (),
    rule_url: str | None = None,
    status: str = "answered",
    pass_number: int = 1,
) -> dict:
    return {
        "ok": True,
        "question_id": question_id,
        "key": "model",
        "run": pass_number,
        "history": [],
        "answer": {"status": "answered", "sources": [{"url": "/raw-only"}]},
        "verified": {
            "status": status,
            "sources": [{"url": url} for url in urls],
            "rule_verbatim": {"source": {"url": rule_url}} if rule_url else None,
        },
    }


def test_counts_verified_answered_replies_by_turn_not_history() -> None:
    counted = sources.count(
        [
            record(),
            record("C1-t1", urls=("/data",)),
            record("C1-t2"),
            record("C1-t2", urls=("/data",), pass_number=2),
            record("C1-t5"),
            record(status="blocked"),
            record(status="need_more_detail"),
            record(status="cannot_answer"),
            record(status="talk_to_a_person"),
            record(status="error"),
            {"ok": False},
        ]
    )

    first = counted["groups"]["first_question"]
    follow = counted["groups"]["follow_up"]
    assert first["answered"] == 2
    assert first["no_sources"] == 1
    assert first["no_sources_percent"] == 50
    assert first["no_sources_cases"] == [
        {"question_id": "G001", "key": "model", "pass": 1}
    ]
    assert follow["answered"] == 3
    assert follow["no_sources"] == 2
    assert follow["no_sources_percent"] == 66.67
    assert [case["question_id"] for case in follow["no_sources_cases"]] == [
        "C1-t2",
        "C1-t5",
    ]
    assert counted["excluded_other_statuses"] == 5
    assert counted["excluded_failed_calls"] == 1


def test_quote_omissions_are_separate_and_can_overlap_empty_lists() -> None:
    counted = sources.count(
        [
            record(urls=("/other",), rule_url="/data"),
            record(rule_url="/data"),
            record(urls=("/data",), rule_url="/data"),
        ]
    )["groups"]["first_question"]

    assert counted["answered"] == 3
    assert counted["no_sources"] == 1
    assert counted["quoted_page_missing"] == 2


def test_a_nonempty_list_is_not_treated_as_correct_or_as_missing() -> None:
    record_list = [record(urls=("/ai-toolkit/projects",))]
    counted = sources.count(record_list)

    assert counted["groups"]["first_question"]["no_sources"] == 0
    assert record_list[0]["verified"]["sources"] == [{"url": "/ai-toolkit/projects"}]


def test_empty_groups_have_no_percentage() -> None:
    counted = sources.count([])

    for group in counted["groups"].values():
        assert group["answered"] == 0
        assert group["no_sources"] == 0
        assert group["no_sources_percent"] is None


@pytest.mark.parametrize("question_id", ["C1", "C1-t0", "unknown"])
def test_unknown_turn_ids_are_not_silently_counted_as_first_questions(
    question_id: str,
) -> None:
    records = [record(question_id)]
    with pytest.raises(ValueError, match="Unrecognised evaluation question ID"):
        sources.count(records)


def test_missing_verified_data_is_not_counted_as_an_empty_list() -> None:
    incomplete = record()
    del incomplete["verified"]
    with pytest.raises(KeyError, match="verified"):
        sources.count([incomplete])


def test_invalid_source_list_is_reported() -> None:
    invalid = record()
    invalid["verified"]["sources"] = None
    with pytest.raises(ValueError, match="Expected a saved source list"):
        sources.count([invalid])


def test_imported_metadata_does_not_invent_question_scope_or_setup_counts(
    tmp_path: Path,
) -> None:
    runs.write_meta(
        tmp_path,
        date="2026-09-21",
        passes=3,
        prompt="not recorded",
        content_ref="old-content",
    )
    runs.write_answers(tmp_path, [record()])

    report = sources.report(tmp_path)

    assert report["questions"] is None
    assert report["unscored_turns_not_persisted"] is None
    assert report["groups"]["first_question"]["answered"] == 1


def test_sources_command_reads_saved_answers_without_preparation_or_rewriting(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from evals import setup

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Offline source analysis must not prepare a model or fetch content")

    monkeypatch.setattr(setup, "prepare", forbidden)
    monkeypatch.setattr(setup, "content", forbidden)
    runs.write_meta(
        tmp_path,
        date="2026-11-06",
        questions="all",
        passes=3,
        prompt="saved-prompt",
        content_ref="saved-content",
        unscored_turns=78,
    )
    runs.write_answers(tmp_path, [record(), record("C1-t2")])
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}

    args = parser().parse_args(["sources", str(tmp_path)])
    args.handler(args)

    report = json.loads(capsys.readouterr().out)[0]
    assert report["unscored_turns_not_persisted"] == 78
    assert report["groups"]["first_question"]["no_sources"] == 1
    assert report["groups"]["follow_up"]["no_sources"] == 1
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before
