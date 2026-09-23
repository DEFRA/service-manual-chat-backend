from logging import getLogger
from typing import Annotated

from fastapi import APIRouter, Depends

from app.ask.engine import AnswerEngine, get_engine
from app.ask.schemas import Answer, AskRequest

router = APIRouter()
logger = getLogger(__name__)


@router.post("/ask")
async def ask(
    body: AskRequest, engine: Annotated[AnswerEngine, Depends(get_engine)]
) -> Answer:
    # The question is what a person typed and may say anything about them, so
    # it never reaches the logs. Length and whether it is a follow-up do.
    logger.info(
        "ask question_length=%d follow_up=%s",
        len(body.question),
        body.previous_question is not None,
    )
    return await engine(body.question, body.previous_question)
