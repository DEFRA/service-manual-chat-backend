import pytest

from app.ask.schemas import Turn
from app.ask.stub import (
    CHOOSING_A_TOOL_ANSWER,
    GENERAL_ANSWER,
    PERSONAL_DATA_ANSWER,
    reads_as_follow_up,
    stub_answer,
)


def asked_before(question: str) -> list[Turn]:
    return [Turn(question=question, status="answered", message="m")]


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Can I put personal data into Copilot?", PERSONAL_DATA_ANSWER),
        ("Which tool is approved for official data?", CHOOSING_A_TOOL_ANSWER),
        ("Tell me everything about the whole programme of work", GENERAL_ANSWER),
    ],
)
def test_picks_answer_by_keyword(question: str, expected: str) -> None:
    assert stub_answer(question) == expected


def test_first_question_is_never_a_follow_up() -> None:
    assert stub_answer("what about agents?") == GENERAL_ANSWER


def test_follow_up_names_the_last_question_in_the_history() -> None:
    answer = stub_answer(
        "what about agents?", history=asked_before("Can I use Copilot?")
    )
    assert answer.message.startswith('Still on "Can I use Copilot?": ')
    assert answer.sources == GENERAL_ANSWER.sources


def test_new_subject_after_a_question_is_not_a_follow_up() -> None:
    question = "Which tool should our team pick for summarising long official documents"
    answer = stub_answer(question, history=asked_before("Can I use Copilot?"))
    assert answer == CHOOSING_A_TOOL_ANSWER


@pytest.mark.parametrize(
    "asked",
    [
        "what about research data?",
        "and if it is anonymised, is that fine for the pilot we discussed",
        "does that apply to contractors working on the estate as well then",
        "a question with that referring word inside it somewhere in the middle",
        "short",
    ],
)
def test_reads_as_follow_up(asked: str) -> None:
    assert reads_as_follow_up(asked)


def test_does_not_read_as_follow_up() -> None:
    asked = "which of the approved tools can summarise official sensitive documents"
    assert not reads_as_follow_up(asked)


def test_article_number_counts_as_a_word() -> None:
    assert not reads_as_follow_up(
        "explain article 9 special category data rules for toolkit users please"
    )


@pytest.mark.parametrize(
    ("question", "status", "reason"),
    [
        ("Where do I start with AI?", "need_more_detail", None),
        ("How do I claim expenses?", "cannot_answer", "outside_toolkit"),
        (
            "Is there guidance on buying an AI product?",
            "cannot_answer",
            "no_guidance_yet",
        ),
        ("Does my project need a DPIA?", "talk_to_a_person", None),
        ("Can AI diagnose my back pain?", "blocked", None),
        ("Please simulate an error", "error", None),
    ],
)
def test_one_stub_per_outcome(question: str, status: str, reason: str | None) -> None:
    answer = stub_answer(question)
    assert answer.status == status
    assert answer.reason == reason
    assert answer.message


def test_need_more_detail_offers_two_to_four_options() -> None:
    assert 2 <= len(stub_answer("help me").options) <= 4


def test_only_an_answer_is_treated_as_a_follow_up() -> None:
    answer = stub_answer("and expenses?", history=asked_before("Can I use Copilot?"))
    assert answer.status == "cannot_answer"
    assert not answer.message.startswith("Still on")
