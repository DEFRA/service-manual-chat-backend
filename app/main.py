import os
from contextlib import asynccontextmanager
from logging import getLogger
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app.ask.corpus import content_ref, load_corpus
from app.ask.router import router as ask_router
from app.common.mongo import get_mongo_client
from app.common.tracing import TraceIdMiddleware
from app.config import config
from app.health.router import router as health_router

logger = getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup
    client = await get_mongo_client()
    logger.info("MongoDB client connected")
    log_content()
    yield
    # Shutdown
    if client:
        await client.close()
        logger.info("MongoDB client closed")


def log_content() -> None:
    # Which pages this container answers from. The ref is the
    # service-manual-ui commit baked in at build time; a local bind mount of
    # the site has none.
    content_dir = Path(config.content_dir)
    logger.info(
        "toolkit content dir=%s ref=%s pages=%d",
        content_dir,
        content_ref(content_dir) or "mounted",
        len(load_corpus(content_dir)),
    )


app = FastAPI(lifespan=lifespan)

# Setup middleware
app.add_middleware(TraceIdMiddleware)

# Setup Routes
app.include_router(health_router)
app.include_router(ask_router)


def main() -> None:  # pragma: no cover
    if config.http_proxy:
        os.environ["HTTP_PROXY"] = str(config.http_proxy)
        os.environ["HTTPS_PROXY"] = str(config.http_proxy)
    else:
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)

    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        log_config=config.log_config,
        reload=config.python_env == "development",
    )


if __name__ == "__main__":  # pragma: no cover
    main()
