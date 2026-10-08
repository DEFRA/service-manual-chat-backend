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


def log_content(cfg: app_config.AppConfig) -> None:
    # Which pages this container answers from. The ref is the
    # service-manual-ui commit baked in at build time; a local bind mount of
    # the site has none.
    content_dir = Path(cfg.content_dir)
    logger.info(
        "toolkit content dir=%s ref=%s pages=%d",
        content_dir,
        corpus.content_ref(content_dir) or "mounted",
        len(corpus.load_corpus(content_dir)),
    )


def create_app(cfg: app_config.AppConfig | None = None) -> fastapi.FastAPI:
    resolved_cfg = cfg or app_config.config

    @contextlib.asynccontextmanager
    async def lifespan(_: fastapi.FastAPI) -> collections.abc.AsyncGenerator[None]:
        client = await mongo.get_mongo_client()
        logger.info("MongoDB client connected")
        log_content(resolved_cfg)
        yield
        if client:
            await client.close()
            logger.info("MongoDB client closed")

    fastapi_app = fastapi.FastAPI(lifespan=lifespan)
    fastapi_app.add_middleware(tracing.TraceIdMiddleware)
    fastapi_app.include_router(health_router.router)
    fastapi_app.include_router(ask_router.router)
    return fastapi_app


def main() -> None:  # pragma: no cover
    cfg = app_config.config
    if cfg.http_proxy:
        os.environ["HTTP_PROXY"] = str(cfg.http_proxy)
        os.environ["HTTPS_PROXY"] = str(cfg.http_proxy)
    else:
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)

    uvicorn.run(
        "app.entrypoints.http:create_app",
        host=cfg.host,
        port=cfg.port,
        log_config=cfg.log_config,
        reload=cfg.python_env == "development",
        factory=True,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
