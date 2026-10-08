"""Testcontainers MongoDB support for testing real Mongo storage."""

import collections.abc
import typing

import pymongo
import pytest
import pytest_asyncio
from testcontainers.community import mongodb as testcontainers_mongodb

# Same image as compose.yml, so the tests run against what the service runs
# against.
MONGO_IMAGE = (
    "mongo@sha256:4510cf3d7050003e958745adb25d2deb3fb907430716162d9cc1a92eda2a6047"
)


@pytest.fixture(scope="session")
def mongo_container() -> collections.abc.Iterator[
    testcontainers_mongodb.MongoDbContainer
]:
    with testcontainers_mongodb.MongoDbContainer(MONGO_IMAGE) as container:
        yield container


@pytest.fixture(scope="session")
def mongo_uri(mongo_container: testcontainers_mongodb.MongoDbContainer) -> str:
    return mongo_container.get_connection_url()


@pytest_asyncio.fixture(scope="session")
async def mongo_database(
    mongo_uri: str,
) -> collections.abc.AsyncIterator[typing.Any]:
    """A session-scoped database on the test container.

    A session scope lets one override cover every TestClient-based test.
    """
    client: pymongo.AsyncMongoClient = pymongo.AsyncMongoClient(mongo_uri)

    yield client["test-database"]

    await client.drop_database("test-database")
    await client.close()


class _ClientProxy:
    """Forwards to the real client, but close() is a no-op.

    The app lifespan closes the client it is given; the shared test client must
    outlive it, and is closed by the `mongo_database` fixture instead.
    """

    def __init__(self, wrapped: typing.Any) -> None:
        self._wrapped = wrapped

    def __getattr__(self, item: str) -> typing.Any:
        return getattr(self._wrapped, item)

    async def close(self) -> None:
        return None


@pytest_asyncio.fixture(scope="session", autouse=True)
async def override_app_mongo(
    mongo_database: typing.Any,
) -> collections.abc.AsyncIterator[None]:
    """Make the app use the test Mongo client.

    `get_mongo_client` returns the module-level `app.common.mongo.client` as-is
    once set, so pre-populating it lets the real function run unmodified and the
    lifespan gets the test database instead of connecting to the default
    `MONGO_URI`. The unit tests of `get_mongo_client` reset this global per test.
    """
    from app.common import mongo as app_mongo

    app_mongo.client = typing.cast(typing.Any, _ClientProxy(mongo_database.client))
    yield
    app_mongo.client = None
