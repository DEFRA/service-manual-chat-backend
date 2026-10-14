from logging import getLogger
from typing import Annotated

from fastapi import APIRouter, Depends

from app.ask import engine as engine_module
from app.ask import schemas

router = APIRouter()
logger = getLogger(__name__)


@router.post("/ask")
async def ask(
    body: schemas.AskRequest,
    engine: Annotated[engine_module.AnswerEngine, Depends(engine_module.get_engine)],
) -> schemas.Answer:
    # The question is what a person typed and may say anything about them, so
    # it never reaches the logs. Length and how much history came with it do.
    history = body.conversation()
    logger.info(
        "ask question_length=%d history_turns=%d",
        len(body.question),
        len(history),
    )
    return await engine(body.question, history)
