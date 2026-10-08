import logging
import typing

import fastapi

from app.ask import engine as engine_mod
from app.ask import schemas

router = fastapi.APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ask")
async def ask(
    body: schemas.AskRequest,
    engine: typing.Annotated[
        engine_mod.AnswerEngine, fastapi.Depends(engine_mod.get_engine)
    ],
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
