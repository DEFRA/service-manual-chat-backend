"""Answers from Amazon Bedrock through Pydantic AI.

Locally the sandbox is reached with `AWS_BEARER_TOKEN_BEDROCK`, which boto3
picks up on its own, and a plain model id. On CDP the same code is pointed at
an inference profile and given a guardrail. Nothing about the prompt or the
output shape changes between the two.
"""

from functools import lru_cache
from logging import getLogger
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.bedrock import BedrockConverseModel, BedrockModelSettings
from pydantic_ai.providers.bedrock import BedrockProvider

from app.ask.corpus import as_context, load_corpus, verify
from app.ask.schemas import Answer
from app.config import config

logger = getLogger(__name__)

# Models that return 403 "your request did not allow prompt caching" when sent
# a cache point. Matched as a substring so an inference profile ARN that
# carries the model id is caught too.
MODELS_WITHOUT_PROMPT_CACHING = ("anthropic.claude-3-haiku",)


def caches_instructions(model_id: str) -> bool:
    return not any(name in model_id for name in MODELS_WITHOUT_PROMPT_CACHING)


def model_settings() -> BedrockModelSettings:
    settings = BedrockModelSettings(
        # The instructions carry the whole toolkit, so cache them across calls.
        # Bedrock keeps the cache for 5 minutes; a read costs a tenth of a
        # fresh input token.
        bedrock_cache_instructions=caches_instructions(config.bedrock_model_id),
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
    # service runs. The corpus is small enough to reload too. Nothing that
    # changes per request belongs in here: the cache key is this exact text.
    prompt = Path(config.system_prompt_path).read_text(encoding="utf-8")
    corpus = load_corpus(Path(config.content_dir))
    return f"{prompt}\n\n# The toolkit pages\n\n{as_context(corpus)}"


@lru_cache(maxsize=2)
def agent_for(instructions_text: str) -> Agent[None, Answer]:
    # The instructions go in as a string, not a function. Pydantic AI only
    # places the Bedrock cache point after static instructions, so a function
    # here means no cache point and every question paying full price. One
    # agent per distinct text: editing the prompt builds a new one.
    model = BedrockConverseModel(
        config.bedrock_model_id,
        provider=BedrockProvider(region_name=config.bedrock_region),
    )
    return Agent(
        model,
        output_type=Answer,
        instructions=instructions_text,
        model_settings=model_settings(),
        retries=2,
    )


def agent() -> Agent[None, Answer]:
    return agent_for(instructions())


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
        "bedrock answered model=%s input_tokens=%s output_tokens=%s "
        "cache_read_tokens=%s cache_write_tokens=%s",
        config.bedrock_model_id,
        usage.input_tokens,
        usage.output_tokens,
        usage.cache_read_tokens,
        usage.cache_write_tokens,
    )
    return verify(result.output, load_corpus(Path(config.content_dir)))
