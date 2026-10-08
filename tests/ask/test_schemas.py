import typing

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

    def test_cannot_answer_rejects_daily_limit(self) -> None:
        reason: typing.Any = "daily_limit"

        with pytest.raises(ValueError, match="outside_toolkit or no_guidance_yet"):
            schemas.Answer(status="cannot_answer", message="m", reason=reason)

    def test_reason_belongs_to_cannot_answer_or_error_only(self) -> None:
        with pytest.raises(ValueError, match="reason belongs"):
            schemas.Answer(status="blocked", message="m", reason="outside_toolkit")

    def test_error_can_carry_the_daily_limit_reason(self) -> None:
        answer = schemas.Answer(status="error", message="m", reason="daily_limit")

        assert answer.reason == "daily_limit"

    def test_error_without_a_reason_is_still_valid(self) -> None:
        answer = schemas.Answer(status="error", message="m")

        assert answer.reason is None

    def test_error_rejects_a_cannot_answer_reason(self) -> None:
        with pytest.raises(ValueError, match="error takes daily_limit or no reason"):
            schemas.Answer(status="error", message="m", reason="outside_toolkit")

    def test_daily_limit_is_rejected_outside_error(self) -> None:
        with pytest.raises(
            ValueError, match="reason belongs to cannot_answer or error only"
        ):
            schemas.Answer(status="blocked", message="m", reason="daily_limit")

    def test_only_an_answer_quotes_a_rule(self) -> None:
        rule = schemas.RuleVerbatim(text="x", source=SOURCE)
        with pytest.raises(ValueError, match="only an answer"):
            schemas.Answer(status="talk_to_a_person", message="m", rule_verbatim=rule)

    def test_status_outside_the_six_is_rejected(self) -> None:
        status: typing.Any = "thinking"

        with pytest.raises(ValueError, match="Input should be"):
            schemas.Answer(status=status, message="m")

    def test_model_answer_never_offers_daily_limit_as_a_reason(self) -> None:
        reason: typing.Any = "daily_limit"

        with pytest.raises(ValueError, match="reason"):
            schemas.ModelAnswer(status="cannot_answer", message="m", reason=reason)

    def test_model_answer_rejects_a_reason_on_error(self) -> None:
        with pytest.raises(ValueError, match="reason belongs to cannot_answer only"):
            schemas.ModelAnswer(status="error", message="m", reason="outside_toolkit")

    def test_model_answer_cannot_answer_still_needs_a_reason(self) -> None:
        with pytest.raises(ValueError, match="needs a reason"):
            schemas.ModelAnswer(status="cannot_answer", message="m")

    def test_every_model_answer_is_also_a_valid_answer(self) -> None:
        model_answer = schemas.ModelAnswer(
            status="cannot_answer", message="m", reason="outside_toolkit"
        )

        answer = schemas.Answer.model_validate(model_answer.model_dump())

        assert answer.reason == "outside_toolkit"
