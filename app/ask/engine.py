"""Which thing answers a question.

`stub` needs nothing and is the default, so `docker compose up` works with no
key. `bedrock` talks to Amazon Bedrock: the sandbox with a bearer token
locally, an inference profile and guardrail on CDP.
"""

from collections import abc

from app import config as app_config
from app.ask import schemas, stub

AnswerEngine = abc.Callable[[str, list[schemas.Turn]], abc.Awaitable[schemas.Answer]]


async def stub_engine(
    question: str, history: list[schemas.Turn]
) -> schemas.Answer:  # NOSONAR
    # Nothing to await, but an engine is awaitable so the router need not care.
    return stub.stub_answer(question, history)


def get_engine() -> AnswerEngine:
    if app_config.config.ask_engine == "bedrock":
        # Imported here so the stub needs neither boto3 nor a region to run.
        from app.ask import bedrock

        return bedrock.bedrock_engine
    return stub_engine
