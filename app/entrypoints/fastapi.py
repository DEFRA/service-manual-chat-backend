import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from logging import getLogger
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app import config
from app.ask import corpus
from app.ask import router as ask_router
from app.common import mongo, tracing
from app.health import router as health_router

logger = getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Startup
    client = await mongo.get_mongo_client()
    logger.info("MongoDB client connected")
    log_content()
    if config.config.ask_engine == "bedrock":
        # Imported here so the stub engine needs neither boto3 nor a region
        # to start, matching app/ask/engine.py's get_engine().
        from app.ask import bedrock

        await bedrock.ensure_ask_daily_usage_index()
    yield
    # Shutdown
    if client:
        await client.close()
        logger.info("MongoDB client closed")


def log_content() -> None:
    # Which pages this container answers from. The ref is the
    # service-manual-ui commit baked in at build time; a local bind mount of
    # the site has none.
    content_dir = Path(config.config.content_dir)
    logger.info(
        "toolkit content dir=%s ref=%s pages=%d",
        content_dir,
        corpus.content_ref(content_dir) or "mounted",
        len(corpus.load_corpus(content_dir)),
    )


app = FastAPI(lifespan=lifespan)

# Setup middleware
app.add_middleware(tracing.TraceIdMiddleware)

# Setup Routes
app.include_router(health_router.router)
app.include_router(ask_router.router)


def main() -> None:  # pragma: no cover
    if config.config.http_proxy:
        os.environ["HTTP_PROXY"] = str(config.config.http_proxy)
        os.environ["HTTPS_PROXY"] = str(config.config.http_proxy)
    else:
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)

    uvicorn.run(
        "app.entrypoints.fastapi:app",
        host=config.config.host,
        port=config.config.port,
        log_config=config.config.log_config,
        reload=config.config.python_env == "development",
    )


if __name__ == "__main__":  # pragma: no cover
    main()
