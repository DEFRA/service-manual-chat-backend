from evals.judge import merge_verdicts


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
