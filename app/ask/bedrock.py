"""Answers from Amazon Bedrock through Pydantic AI.

Locally the sandbox is reached with `AWS_BEARER_TOKEN_BEDROCK`, which boto3
picks up on its own, and a plain model id. On CDP the same code is pointed at
an inference profile and given a guardrail. Nothing about the prompt or the
output shape changes between the two.
"""

from functools import cache
from logging import getLogger
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.bedrock import BedrockConverseModel, BedrockModelSettings
from pydantic_ai.providers.bedrock import BedrockProvider

from app.ask.corpus import as_context, load_corpus, verify
from app.ask.schemas import Answer
from app.config import config

logger = getLogger(__name__)


def model_settings() -> BedrockModelSettings:
    settings = BedrockModelSettings(
        # The instructions carry the whole toolkit, so cache them across calls.
        bedrock_cache_instructions=True,
    )
    if config.bedrock_guardrail_id:
        settings["bedrock_guardrail_config"] = {
            "guardrailIdentifier": config.bedrock_guardrail_id,
            "guardrailVersion": config.bedrock_guardrail_version or "DRAFT",
            "trace": "enabled",
        }
    return settings


def instructions() -> str:
    # Read on every question so the prompt file can be edited while the
    # service runs. The corpus is small enough to reload too.
    prompt = Path(config.system_prompt_path).read_text(encoding="utf-8")
    corpus = load_corpus(Path(config.content_dir))
    return f"{prompt}\n\n# The toolkit pages\n\n{as_context(corpus)}"


@cache
def agent() -> Agent[None, Answer]:
    model = BedrockConverseModel(
        config.bedrock_model_id,
        provider=BedrockProvider(region_name=config.bedrock_region),
    )
    return Agent(
        model,
        output_type=Answer,
        instructions=instructions,
        model_settings=model_settings(),
        retries=2,
    )


def user_prompt(question: str, previous_question: str | None) -> str:
    if previous_question:
        return (
            f"Previous question, already answered: {previous_question}\n\n"
            f"Follow-up question: {question}"
        )
    return f"Question: {question}"


ERROR_ANSWER = Answer(
    status="error",
    message="The toolkit could not answer just now. Try again in a minute.",
)


async def bedrock_engine(question: str, previous_question: str | None) -> Answer:
    try:
        result = await agent().run(user_prompt(question, previous_question))
    except Exception:
        # Whatever went wrong between here and the model: timeout, throttling,
        # an output that never validated. The reader gets the error outcome
        # with their question kept; the cause goes to the logs, never the
        # question.
        logger.exception("bedrock gave no answer model=%s", config.bedrock_model_id)
        return ERROR_ANSWER
    usage = result.usage
    logger.info(
        "bedrock answered model=%s input_tokens=%s output_tokens=%s",
        config.bedrock_model_id,
        usage.input_tokens,
        usage.output_tokens,
    )
    return verify(result.output, load_corpus(Path(config.content_dir)))
