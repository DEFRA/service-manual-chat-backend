import json

from evals.judge import PROMPT, Verdict, merge_verdicts, shown_to_judge


def verdict(qid, run=1, **marks):
    return {"key": "sonnet-4-6", "run": run, "question_id": qid, "marks": marks}


OLD = [
    verdict(
        "G041",
        grounded_in_named_sources=True,
        grounded_in_toolkit=True,
        complete=True,
        reason="nothing",
    )
]


def test_a_full_re_judge_replaces_the_record():
    fresh = [
        verdict(
            "G041",
            grounded_in_named_sources=False,
            grounded_in_toolkit=True,
            complete=False,
            reason="x",
        )
    ]
    merged = merge_verdicts(OLD, fresh)
    assert merged[0]["marks"]["complete"] is False


def test_a_partial_re_judge_keeps_the_verdicts_it_was_not_asked_for():
    # Re-judging for right_rule must not move Grounded or Complete: those figures are
    # already recorded in the set's change log.
    fresh = [
        verdict(
            "G041",
            grounded_in_named_sources=False,
            complete=False,
            right_rule=False,
            reason="wrong rule",
        )
    ]
    merged = merge_verdicts(OLD, fresh, only=["right_rule"])
    marks = merged[0]["marks"]
    assert marks["complete"] is True
    assert marks["grounded_in_named_sources"] is True
    assert marks["reason"] == "nothing"
    assert marks["right_rule"] is False
    assert marks["right_rule_reason"] == "wrong rule"


def test_records_not_re_judged_are_untouched_and_new_ones_are_added():
    fresh = [verdict("G042", right_rule=True, reason="r")]
    merged = merge_verdicts(OLD, fresh, only=["right_rule"])
    assert [m["question_id"] for m in merged] == ["G041", "G042"]
    assert merged[0]["marks"] == OLD[0]["marks"]


INCIDENT = "/ai-toolkit/guidance/report-an-ai-incident"
DATA_SAFE = "/ai-toolkit/guidance/keeping-data-safe"
TITLES = {INCIDENT: "Report an AI incident", DATA_SAFE: "Keeping data safe"}


def test_the_judge_sees_a_wrong_page_quote_the_reader_did_not():
    # J11 in hand-check sample 2: row 41 names Report an AI incident, the quote came
    # from Keeping data safe, and the old backend check dropped it before display.
    quote = {
        "text": "You must remove all personal data",
        "source": {"title": "Keeping data safe", "url": DATA_SAFE},
    }
    record = {
        "answer": {
            "status": "answered",
            "message": "Stop using the tool.",
            "rule_verbatim": quote,
        },
        "verified": {
            "status": "answered",
            "message": "Stop using the tool.",
            "rule_verbatim": None,
        },
    }
    question = {
        "question": "What do I do if I put personal data into an AI tool?",
        "expected_status": ["answered"],
        "expected_answer": "The four steps.",
        "expects_rule": True,
        "expected_pages": [INCIDENT],
    }
    shown = shown_to_judge(record, question, TITLES)
    assert f"Named source pages: Report an AI incident ({INCIDENT})" in shown
    answer = json.loads(shown.split("Answer to score:\n", 1)[1])
    assert answer["rule_verbatim"]["source"]["url"] == DATA_SAFE


def test_the_judge_is_told_a_wrong_page_quote_fails_grounded_even_when_the_point_is_on_the_named_page():
    # J06: row 4's answer quoted Keeping data safe for a point Using data with AI also
    # makes, and the judge passed it because the quote added no new facts.
    flat = " ".join(PROMPT.split())
    assert (
        "fails grounded_in_named_sources, even when the message around it is grounded"
        in flat
    )
    assert "even when the same point is on the named page" in flat
    # Row 4 expects no quote, and the judge then excused it: "no quoted rule was expected".
    assert "whether or not a quoted rule is expected" in flat


def test_the_judge_gives_its_reason_before_its_verdicts():
    # J06 on 30 September: the reason ended "This fails grounded_in_named_sources"
    # after the verdict had already been written as a pass.
    assert list(Verdict.model_json_schema()["properties"])[0] == "reason"
    assert "before the verdicts" in " ".join(PROMPT.split())
