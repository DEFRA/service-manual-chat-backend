import pytest

from app.ask import schemas

SOURCE = schemas.Source(title="t", url="/ai-toolkit")


class TestSchemas:
    def test_answered_is_the_default_shape(self) -> None:
        answer = schemas.Answer(status="answered", message="m")

        assert answer.model_dump() == {
            "status": "answered",
            "message": "m",
            "rule_verbatim": None,
            "sources": [],
            "options": [],
            "reason": None,
        }

    @pytest.mark.parametrize("count", [1, 5])
    def test_need_more_detail_needs_two_to_four_options(self, count: int) -> None:
        with pytest.raises(ValueError, match="2 to 4 options"):
            schemas.Answer(
                status="need_more_detail", message="m", options=["o"] * count
            )

    def test_options_belong_to_need_more_detail_only(self) -> None:
        with pytest.raises(ValueError, match="options belong"):
            schemas.Answer(status="answered", message="m", options=["a", "b"])

    def test_cannot_answer_needs_a_reason(self) -> None:
        with pytest.raises(ValueError, match="needs a reason"):
            schemas.Answer(status="cannot_answer", message="m")

    def test_reason_belongs_to_cannot_answer_only(self) -> None:
        with pytest.raises(ValueError, match="reason belongs"):
            schemas.Answer(status="blocked", message="m", reason="outside_toolkit")

    def test_only_an_answer_quotes_a_rule(self) -> None:
        rule = schemas.RuleVerbatim(text="x", source=SOURCE)
        with pytest.raises(ValueError, match="only an answer"):
            schemas.Answer(status="talk_to_a_person", message="m", rule_verbatim=rule)

    def test_status_outside_the_six_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Input should be"):
            schemas.Answer(status="thinking", message="m")  # type: ignore[arg-type]
