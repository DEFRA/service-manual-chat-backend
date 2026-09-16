from logging import getLogger

from fastapi import APIRouter, Depends

from app.common.http_client import create_async_client
from app.common.mongo import get_db
from app.config import config

router = APIRouter(prefix="/example")
logger = getLogger(__name__)


# basic endpoint example
@router.get("/test")
async def root():
    logger.info("TEST ENDPOINT")
    return {"ok": True}


# database endpoint example
@router.get("/db")
async def db_query(db=Depends(get_db)):
    await db.example.insert_one({"foo": "bar"})
    data = await db.example.find_one({}, {"_id": 0})
    return {"ok": data}


# http client endpoint example
@router.get("/http")
async def http_query(client=Depends(create_async_client)):
    endpoint = config.aws_endpoint_url or "http://localstack:4566"
    resp = await client.get(f"{endpoint}/health")
    return {"ok": resp.status_code}
