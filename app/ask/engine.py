"""Which thing answers a question.

`stub` needs nothing and is the default, so `docker compose up` works with no
key. `bedrock` talks to Amazon Bedrock: the sandbox with a bearer token
locally, an inference profile and guardrail on CDP.
"""

from collections.abc import Awaitable, Callable

from app.ask.schemas import Answer
from app.ask.stub import stub_answer
from app.config import config

AnswerEngine = Callable[[str, str | None], Awaitable[Answer]]


async def stub_engine(question: str, previous_question: str | None) -> Answer:
    return stub_answer(question, previous_question)


def get_engine() -> AnswerEngine:
    if config.ask_engine == "bedrock":
        # Imported here so the stub needs neither boto3 nor a region to run.
        from app.ask.bedrock import bedrock_engine

        return bedrock_engine
    return stub_engine
