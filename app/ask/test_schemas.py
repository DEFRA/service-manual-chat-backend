import pytest
from pydantic import ValidationError

from app.ask.schemas import Answer, RuleVerbatim, Source

SOURCE = Source(title="t", url="/ai-toolkit")


def test_answered_is_the_default_shape():
    answer = Answer(status="answered", message="m")
    assert answer.model_dump() == {
        "status": "answered",
        "message": "m",
        "rule_verbatim": None,
        "sources": [],
        "options": [],
        "reason": None,
    }


@pytest.mark.parametrize("count", [1, 5])
def test_need_more_detail_needs_two_to_four_options(count):
    with pytest.raises(ValidationError, match="2 to 4 options"):
        Answer(status="need_more_detail", message="m", options=["o"] * count)


def test_options_belong_to_need_more_detail_only():
    with pytest.raises(ValidationError, match="options belong"):
        Answer(status="answered", message="m", options=["a", "b"])


def test_cannot_answer_needs_a_reason():
    with pytest.raises(ValidationError, match="needs a reason"):
        Answer(status="cannot_answer", message="m")


def test_cannot_answer_rejects_daily_limit():
    with pytest.raises(ValidationError, match="outside_toolkit or no_guidance_yet"):
        Answer(status="cannot_answer", message="m", reason="daily_limit")


def test_reason_belongs_to_cannot_answer_or_error_only():
    with pytest.raises(ValidationError, match="reason belongs"):
        Answer(status="blocked", message="m", reason="outside_toolkit")


def test_error_can_carry_the_daily_limit_reason():
    answer = Answer(status="error", message="m", reason="daily_limit")
    assert answer.reason == "daily_limit"


def test_error_without_a_reason_is_still_valid():
    answer = Answer(status="error", message="m")
    assert answer.reason is None


def test_error_rejects_a_cannot_answer_reason():
    with pytest.raises(ValidationError, match="error takes daily_limit or no reason"):
        Answer(status="error", message="m", reason="outside_toolkit")


def test_daily_limit_is_rejected_outside_error():
    with pytest.raises(
        ValidationError, match="reason belongs to cannot_answer or error only"
    ):
        Answer(status="blocked", message="m", reason="daily_limit")


def test_only_an_answer_quotes_a_rule():
    rule = RuleVerbatim(text="x", source=SOURCE)
    with pytest.raises(ValidationError, match="only an answer"):
        Answer(status="talk_to_a_person", message="m", rule_verbatim=rule)


def test_status_outside_the_six_is_rejected():
    with pytest.raises(ValidationError):
        Answer(status="thinking", message="m")
