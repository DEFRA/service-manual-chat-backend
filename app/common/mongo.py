import logging

import fastapi
import pymongo
from pymongo.asynchronous import database as async_db

from app import config as app_config
from app.common import tls

logger = logging.getLogger(__name__)

client: pymongo.AsyncMongoClient | None = None
db: async_db.AsyncDatabase | None = None


async def get_mongo_client() -> pymongo.AsyncMongoClient:
    global client
    if client is None:
        # Use the custom CA Certs from env vars if set.
        # We can remove this once we migrate to mongo Atlas.
        cert = tls.custom_ca_certs.get(app_config.config.mongo_truststore)
        if cert:
            logger.info(
                "Creating MongoDB client with custom TLS cert %s",
                app_config.config.mongo_truststore,
            )
            client = pymongo.AsyncMongoClient(
                app_config.config.mongo_uri, tlsCAFile=cert
            )
        else:
            logger.info("Creating MongoDB client")
            client = pymongo.AsyncMongoClient(app_config.config.mongo_uri)

        logger.info("Testing MongoDB connection to %s", app_config.config.mongo_uri)
        await check_connection(client)
    return client


def get_db(
    client: pymongo.AsyncMongoClient = fastapi.Depends(get_mongo_client),
) -> async_db.AsyncDatabase:
    global db
    if db is None:
        db = client.get_database(app_config.config.mongo_database)
    return db


async def check_connection(client: pymongo.AsyncMongoClient) -> None:
    database = get_db(client)
    response = await database.command("ping")
    logger.info("MongoDB PING %s", response)
