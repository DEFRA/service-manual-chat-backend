import pytest
from fastapi.testclient import TestClient

from app.ask import engine as engine_mod
from app.ask.engine import get_engine, stub_engine
from app.ask.schemas import MAX_QUESTION_LENGTH
from app.main import app

client = TestClient(app)


def test_ask_returns_the_wire_shape():
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


def test_ask_answers_a_follow_up_against_the_previous_question():
    response = client.post(
        "/ask",
        json={"question": "what about agents?", "previous_question": "Copilot?"},
    )

    assert response.status_code == 200
    assert response.json()["message"].startswith('Still on "Copilot?": ')


def test_ask_can_return_each_of_the_other_outcomes():
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


def test_ask_without_a_rule_sends_null_not_missing():
    response = client.post("/ask", json={"question": "which tool"})

    assert response.json()["rule_verbatim"] is None


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"question": ""},
        {"question": "x" * (MAX_QUESTION_LENGTH + 1)},
    ],
)
def test_ask_rejects_a_bad_question(body):
    assert client.post("/ask", json=body).status_code == 422


def test_get_engine_defaults_to_stub():
    assert get_engine() is stub_engine


def test_get_engine_selects_bedrock(monkeypatch):
    monkeypatch.setattr(engine_mod.config, "ask_engine", "bedrock")

    from app.ask.bedrock import bedrock_engine

    assert get_engine() is bedrock_engine
