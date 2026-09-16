from logging import getLogger

from fastapi import Depends
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.common.tls import custom_ca_certs
from app.config import config

logger = getLogger(__name__)

client: AsyncMongoClient | None = None
db: AsyncDatabase | None = None


async def get_mongo_client() -> AsyncMongoClient:
    global client
    if client is None:
        # Use the custom CA Certs from env vars if set.
        # We can remove this once we migrate to mongo Atlas.
        cert = custom_ca_certs.get(config.mongo_truststore)
        if cert:
            logger.info(
                "Creating MongoDB client with custom TLS cert %s",
                config.mongo_truststore,
            )
            client = AsyncMongoClient(config.mongo_uri, tlsCAFile=cert)
        else:
            logger.info("Creating MongoDB client")
            client = AsyncMongoClient(config.mongo_uri)

        logger.info("Testing MongoDB connection to %s", config.mongo_uri)
        await check_connection(client)
    return client


async def get_db(client: AsyncMongoClient = Depends(get_mongo_client)) -> AsyncDatabase:
    global db
    if db is None:
        db = client.get_database(config.mongo_database)
    return db


async def check_connection(client: AsyncMongoClient):
    database = await get_db(client)
    response = await database.command("ping")
    logger.info("MongoDB PING %s", response)
