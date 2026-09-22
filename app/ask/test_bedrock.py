from pathlib import Path

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.providers.bedrock import BedrockProvider

from app.ask import bedrock
from app.ask.bedrock import (
    agent,
    bedrock_engine,
    caches_instructions,
    model_settings,
    user_prompt,
)

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


def test_caching_is_off_for_a_model_that_refuses_it(monkeypatch):
    assert caches_instructions("anthropic.claude-sonnet-4-6")
    assert not caches_instructions("anthropic.claude-3-haiku-20240307-v1:0")
    assert not caches_instructions(
        "arn:aws:bedrock:eu-west-2:1:inference-profile/anthropic.claude-3-haiku-x"
    )
    monkeypatch.setattr(
        bedrock.config, "bedrock_model_id", "anthropic.claude-3-haiku-20240307-v1:0"
    )
    assert model_settings()["bedrock_cache_instructions"] is False


async def test_the_request_built_for_bedrock_ends_its_system_prompt_with_a_cache_point():
    # A function passed as instructions is "dynamic" to Pydantic AI, which then
    # sends no cache point at all. Map the messages the agent really sends
    # through the Bedrock model's own mapping and look for the marker.
    seen = {}

    def respond(messages, info: AgentInfo) -> ModelResponse:
        seen["messages"] = messages
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name=info.output_tools[0].name,
                    args={"status": "answered", "message": "m", "sources": []},
                )
            ]
        )

    with agent().override(model=FunctionModel(respond)):
        await bedrock_engine("q", None)

    model = BedrockConverseModel(
        "anthropic.claude-sonnet-4-6",
        provider=BedrockProvider(region_name="eu-west-2"),
    )
    system_prompt, _ = await model._map_messages(
        seen["messages"], ModelRequestParameters(), model_settings()
    )
    assert "Rules and advice are different things" in system_prompt[0]["text"]
    assert "cachePoint" in system_prompt[-1]


async def test_editing_the_prompt_changes_the_next_answer_without_a_restart(
    monkeypatch, tmp_path
):
    prompt = tmp_path / "system.md"
    prompt.write_text("Version one.", encoding="utf-8")
    monkeypatch.setattr(bedrock.config, "system_prompt_path", str(prompt))
    seen = []

    def respond(messages, info: AgentInfo) -> ModelResponse:
        seen.append(messages[0].instructions)
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name=info.output_tools[0].name,
                    args={"status": "answered", "message": "m", "sources": []},
                )
            ]
        )

    with agent().override(model=FunctionModel(respond)):
        await bedrock_engine("q", None)
    prompt.write_text("Version two.", encoding="utf-8")
    with agent().override(model=FunctionModel(respond)):
        await bedrock_engine("q", None)

    assert seen[0].startswith("Version one.")
    assert seen[1].startswith("Version two.")


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
