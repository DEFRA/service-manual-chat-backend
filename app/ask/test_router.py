import typing

import pytest
from fastapi.testclient import TestClient

from app.ask import engine as engine_mod
from app.ask.engine import get_engine, stub_engine
from app.ask.schemas import MAX_HISTORY_TURNS, MAX_MESSAGE_LENGTH, MAX_QUESTION_LENGTH
from app.main import app

client = TestClient(app)
TURN = {"question": "Copilot?", "status": "answered", "message": "m"}


def test_ask_returns_the_wire_shape() -> None:
    response = client.post("/ask", json={"question": "Can I use Copilot?"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["rule_verbatim"]["source"]["url"] == (
        "/ai-toolkit/guidance/using-data-with-ai"
    )
    assert body["sources"][1] == {
        "title": "Microsoft 365 Copilot",
        "url": "/ai-toolkit/tools/microsoft-365-copilot",
        "section": None,
    }


def test_ask_answers_a_follow_up_against_the_history() -> None:
    response = client.post(
        "/ask",
        json={
            "question": "what about agents?",
            "history": [
                {"question": "Parking?", "status": "cannot_answer", "message": "m"},
                {"question": "Copilot?", "status": "answered", "message": "m"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["message"].startswith('Still on "Copilot?": ')


def test_ask_still_takes_the_previous_question_alone() -> None:
    # What the front end sends until it sends history. Remove with the field.
    response = client.post(
        "/ask",
        json={"question": "what about agents?", "previous_question": "Copilot?"},
    )

    assert response.status_code == 200
    assert response.json()["message"].startswith('Still on "Copilot?": ')


def test_history_wins_over_the_previous_question() -> None:
    response = client.post(
        "/ask",
        json={
            "question": "what about agents?",
            "previous_question": "Parking?",
            "history": [{"question": "Copilot?", "status": "answered", "message": "m"}],
        },
    )

    assert response.json()["message"].startswith('Still on "Copilot?": ')


def test_ask_logs_the_number_of_history_turns_and_not_the_words(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO", logger="app.ask.router")
    client.post(
        "/ask",
        json={
            "question": "what about agents?",
            "history": [{"question": "Copilot?", "status": "answered", "message": "m"}],
        },
    )

    assert "history_turns=1" in caplog.text
    assert "Copilot" not in caplog.text
    assert "agents" not in caplog.text


def test_ask_can_return_each_of_the_other_outcomes() -> None:
    for question, status in [
        ("help me", "need_more_detail"),
        ("parking", "cannot_answer"),
        ("my project", "talk_to_a_person"),
        ("medical", "blocked"),
        ("simulate an error", "error"),
    ]:
        assert (
            client.post("/ask", json={"question": question}).json()["status"] == status
        )


def test_ask_without_a_rule_sends_null_not_missing() -> None:
    response = client.post("/ask", json={"question": "which tool"})

    assert response.json()["rule_verbatim"] is None


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"question": ""},
        {"question": "x" * (MAX_QUESTION_LENGTH + 1)},
        {"question": "q", "history": [TURN] * (MAX_HISTORY_TURNS + 1)},
        {
            "question": "q",
            "history": [{**TURN, "message": "x" * (MAX_MESSAGE_LENGTH + 1)}],
        },
        {"question": "q", "history": [{**TURN, "question": ""}]},
        {"question": "q", "history": [{**TURN, "status": "shrug"}]},
        {"question": "q", "history": [{**TURN, "options": ["o"] * 5}]},
    ],
)
def test_ask_rejects_a_bad_request(body: dict[str, typing.Any]) -> None:
    assert client.post("/ask", json=body).status_code == 422


def test_get_engine_defaults_to_stub() -> None:
    assert get_engine() is stub_engine


def test_get_engine_selects_bedrock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine_mod.config, "ask_engine", "bedrock")

    from app.ask.bedrock import bedrock_engine

    assert get_engine() is bedrock_engine
