import collections.abc
import contextlib
import logging
import os
from pathlib import Path

import fastapi
import uvicorn

from app import config as app_config
from app.ask import corpus
from app.ask import router as ask_router
from app.common import mongo, tracing
from app.health import router as health_router

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(_: fastapi.FastAPI) -> collections.abc.AsyncGenerator[None]:
    # Startup
    client = await mongo.get_mongo_client()
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
    content_dir = Path(app_config.config.content_dir)
    logger.info(
        "toolkit content dir=%s ref=%s pages=%d",
        content_dir,
        corpus.content_ref(content_dir) or "mounted",
        len(corpus.load_corpus(content_dir)),
    )


app = fastapi.FastAPI(lifespan=lifespan)

# Setup middleware
app.add_middleware(tracing.TraceIdMiddleware)

# Setup Routes
app.include_router(health_router.router)
app.include_router(ask_router.router)


def main() -> None:  # pragma: no cover
    if app_config.config.http_proxy:
        os.environ["HTTP_PROXY"] = str(app_config.config.http_proxy)
        os.environ["HTTPS_PROXY"] = str(app_config.config.http_proxy)
    else:
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)

    uvicorn.run(
        "app.main:app",
        host=app_config.config.host,
        port=app_config.config.port,
        log_config=app_config.config.log_config,
        reload=app_config.config.python_env == "development",
    )


if __name__ == "__main__":  # pragma: no cover
    main()
