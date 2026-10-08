import collections.abc

import fastapi.testclient
import pytest

from app import main as app_main

pytest_plugins = ["tests.support.mongo"]


@pytest.fixture
def client(
    override_app_mongo: None,  # noqa: ARG001
) -> collections.abc.Iterator[fastapi.testclient.TestClient]:
    with fastapi.testclient.TestClient(app_main.app) as test_client:
        yield test_client
