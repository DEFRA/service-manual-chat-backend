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


def test_reason_belongs_to_cannot_answer_only():
    with pytest.raises(ValidationError, match="reason belongs"):
        Answer(status="blocked", message="m", reason="outside_toolkit")


def test_only_an_answer_quotes_a_rule():
    with pytest.raises(ValidationError, match="only an answer"):
        Answer(
            status="talk_to_a_person",
            message="m",
            rule_verbatim=RuleVerbatim(text="x", source=SOURCE),
        )


def test_status_outside_the_six_is_rejected():
    with pytest.raises(ValidationError):
        Answer(status="thinking", message="m")
