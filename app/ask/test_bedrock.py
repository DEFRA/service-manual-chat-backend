from pathlib import Path

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.ask import bedrock
from app.ask.bedrock import agent, bedrock_engine, model_settings, user_prompt

CONTENT = Path(__file__).parent / "__fixtures__" / "content"


@pytest.fixture(autouse=True)
def _local_content(monkeypatch):
    monkeypatch.setattr(bedrock.config, "content_dir", str(CONTENT))
    monkeypatch.setattr(bedrock.config, "system_prompt_path", "prompts/system.md")


def answer_with(args: dict):
    def respond(_messages, info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=args)]
        )

    return FunctionModel(respond)


def test_user_prompt_carries_the_previous_question():
    assert user_prompt("what about agents?", "Can I use Copilot?") == (
        "Previous question, already answered: Can I use Copilot?\n\n"
        "Follow-up question: what about agents?"
    )
    assert user_prompt("Can I use Copilot?", None) == "Question: Can I use Copilot?"


def test_model_settings_without_a_guardrail_has_no_guardrail_config(monkeypatch):
    monkeypatch.setattr(bedrock.config, "bedrock_guardrail_id", None)
    assert "bedrock_guardrail_config" not in model_settings()
    assert model_settings()["bedrock_cache_instructions"] is True


def test_model_settings_with_a_guardrail(monkeypatch):
    monkeypatch.setattr(bedrock.config, "bedrock_guardrail_id", "gr-1")
    monkeypatch.setattr(bedrock.config, "bedrock_guardrail_version", "3")
    assert model_settings()["bedrock_guardrail_config"] == {
        "guardrailIdentifier": "gr-1",
        "guardrailVersion": "3",
        "trace": "enabled",
    }


async def test_engine_returns_a_verified_answer():
    seen = {}

    def respond(messages, info: AgentInfo) -> ModelResponse:
        seen["instructions"] = messages[0].instructions
        seen["prompt"] = messages[0].parts[0].content
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name=info.output_tools[0].name,
                    args={
                        "status": "answered",
                        "message": "Remove personal data first.",
                        "rule_verbatim": {
                            "text": "For everyday use, remove personal data first.",
                            "source": {
                                "title": "Using data with AI",
                                "url": "/ai-toolkit/guidance/using-data-with-ai",
                            },
                        },
                        "sources": [
                            {
                                "title": "Using data with AI",
                                "url": "/ai-toolkit/guidance/using-data-with-ai",
                            },
                            {"title": "Made up", "url": "/ai-toolkit/not-a-page"},
                        ],
                    },
                )
            ]
        )

    with agent().override(model=FunctionModel(respond)):
        answer = await bedrock_engine("Can I paste personal data in?", None)

    assert answer.rule_verbatim.text == "For everyday use, remove personal data first."
    assert [s.url for s in answer.sources] == [
        "/ai-toolkit/guidance/using-data-with-ai"
    ]
    assert seen["prompt"] == "Question: Can I paste personal data in?"
    assert "Rules and advice are different things" in seen["instructions"]
    assert '<page url="/ai-toolkit/guidance/using-data-with-ai"' in seen["instructions"]


async def test_engine_drops_a_paraphrased_rule():
    with agent().override(
        model=answer_with(
            {
                "status": "answered",
                "message": "m",
                "rule_verbatim": {
                    "text": "Strip out personal data before you use it.",
                    "source": {
                        "title": "t",
                        "url": "/ai-toolkit/guidance/using-data-with-ai",
                    },
                },
                "sources": [],
            }
        )
    ):
        answer = await bedrock_engine("q", None)

    assert answer.rule_verbatim is None


async def test_engine_retries_when_the_model_replies_in_prose():
    calls = []

    def respond(_messages, info: AgentInfo) -> ModelResponse:
        calls.append(1)
        if len(calls) == 1:
            return ModelResponse(parts=[TextPart(content="Here is some prose")])
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name=info.output_tools[0].name,
                    args={"status": "answered", "message": "m", "sources": []},
                )
            ]
        )

    with agent().override(model=FunctionModel(respond)):
        answer = await bedrock_engine("q", None)

    assert answer.message == "m"
    assert len(calls) == 2


async def test_engine_turns_a_failure_into_the_error_outcome():
    def respond(_messages, _info: AgentInfo) -> ModelResponse:
        msg = "throttled"
        raise RuntimeError(msg)

    with agent().override(model=FunctionModel(respond)):
        answer = await bedrock_engine("q", None)

    assert answer.status == "error"
    assert answer.message
