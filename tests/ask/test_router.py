import typing

import fastapi.testclient
import pytest

from app.ask import schemas

TURN = {"question": "Copilot?", "status": "answered", "message": "m"}


class TestAskEndpoint:
    def test_ask_returns_the_wire_shape(
        self, client: fastapi.testclient.TestClient
    ) -> None:
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

    def test_ask_answers_a_follow_up_against_the_history(
        self, client: fastapi.testclient.TestClient
    ) -> None:
        response = client.post(
            "/ask",
            json={
                "question": "what about agents?",
                "history": [
                    {
                        "question": "Parking?",
                        "status": "cannot_answer",
                        "message": "m",
                    },
                    {
                        "question": "Copilot?",
                        "status": "answered",
                        "message": "m",
                    },
                ],
            },
        )

        assert response.status_code == 200
        assert response.json()["message"].startswith('Still on "Copilot?": ')

    def test_ask_still_takes_the_previous_question_alone(
        self, client: fastapi.testclient.TestClient
    ) -> None:
        response = client.post(
            "/ask",
            json={
                "question": "what about agents?",
                "previous_question": "Copilot?",
            },
        )

        assert response.status_code == 200
        assert response.json()["message"].startswith('Still on "Copilot?": ')

    def test_history_wins_over_the_previous_question(
        self, client: fastapi.testclient.TestClient
    ) -> None:
        response = client.post(
            "/ask",
            json={
                "question": "what about agents?",
                "previous_question": "Parking?",
                "history": [
                    {
                        "question": "Copilot?",
                        "status": "answered",
                        "message": "m",
                    }
                ],
            },
        )

        assert response.status_code == 200
        assert response.json()["message"].startswith('Still on "Copilot?": ')

    def test_ask_logs_the_number_of_history_turns_and_not_the_words(
        self, client: fastapi.testclient.TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level("INFO", logger="app.ask.router")
        client.post(
            "/ask",
            json={
                "question": "what about agents?",
                "history": [
                    {
                        "question": "Copilot?",
                        "status": "answered",
                        "message": "m",
                    }
                ],
            },
        )

        assert "history_turns=1" in caplog.text
        assert "Copilot" not in caplog.text
        assert "agents" not in caplog.text

    def test_ask_can_return_each_of_the_other_outcomes(
        self, client: fastapi.testclient.TestClient
    ) -> None:
        for question, status in [
            ("help me", "need_more_detail"),
            ("parking", "cannot_answer"),
            ("my project", "talk_to_a_person"),
            ("medical", "blocked"),
            ("simulate an error", "error"),
        ]:
            res = client.post("/ask", json={"question": question})
            assert res.json()["status"] == status

    def test_ask_without_a_rule_sends_null_not_missing(
        self, client: fastapi.testclient.TestClient
    ) -> None:
        response = client.post("/ask", json={"question": "which tool"})

        assert response.status_code == 200
        assert response.json()["rule_verbatim"] is None

    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"question": ""},
            {"question": "x" * (schemas.MAX_QUESTION_LENGTH + 1)},
            {
                "question": "q",
                "history": [TURN] * (schemas.MAX_HISTORY_TURNS + 1),
            },
            {
                "question": "q",
                "history": [
                    {
                        **TURN,
                        "message": "x" * (schemas.MAX_MESSAGE_LENGTH + 1),
                    }
                ],
            },
            {"question": "q", "history": [{**TURN, "question": ""}]},
            {"question": "q", "history": [{**TURN, "status": "shrug"}]},
            {"question": "q", "history": [{**TURN, "options": ["o"] * 5}]},
        ],
    )
    def test_ask_rejects_a_bad_request(
        self, client: fastapi.testclient.TestClient, body: dict[str, typing.Any]
    ) -> None:
        assert client.post("/ask", json=body).status_code == 422
