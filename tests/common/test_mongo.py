import collections.abc
from unittest import mock

import pytest

from app import config as app_config
from app.common import mongo


@pytest.fixture(autouse=True)
def reset_mongo_client() -> collections.abc.Generator[None]:
    original_client = mongo.client
    original_db = mongo.db
    mongo.client = None
    mongo.db = None
    yield
    mongo.client = original_client
    mongo.db = original_db


class TestMongoClient:
    @pytest.mark.asyncio
    async def test_get_mongo_client_initialization(
        self, mocker: mock.MagicMock
    ) -> None:
        mock_client_cls = mocker.patch("pymongo.AsyncMongoClient")
        mock_instance = mock_client_cls.return_value

        mock_db = mocker.MagicMock()
        mock_instance.get_database.return_value = mock_db
        mock_db.command = mocker.AsyncMock(return_value={"ok": 1})
        client = await mongo.get_mongo_client()

        assert client == mock_instance
        mock_client_cls.assert_called_once_with(app_config.config.mongo_uri)
        mock_db.command.assert_awaited_once_with("ping")

    @pytest.mark.asyncio
    async def test_get_mongo_client_with_custom_tls(
        self, mocker: mock.MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(app_config.config, "mongo_truststore", "custom-cert-key")
        mocker.patch.dict(
            "app.common.tls.custom_ca_certs",
            {"custom-cert-key": "/path/to/cert.pem"},
        )

        mock_client_cls = mocker.patch("pymongo.AsyncMongoClient")
        mock_instance = mock_client_cls.return_value
        mock_db = mocker.MagicMock()
        mock_instance.get_database.return_value = mock_db
        mock_db.command = mocker.AsyncMock(return_value={"ok": 1})

        await mongo.get_mongo_client()

        mock_client_cls.assert_called_once_with(
            app_config.config.mongo_uri, tlsCAFile="/path/to/cert.pem"
        )

    @pytest.mark.asyncio
    async def test_get_mongo_client_returns_existing(
        self, mocker: mock.MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        existing_client = mocker.Mock()
        monkeypatch.setattr(mongo, "client", existing_client)

        mock_client_cls = mocker.patch("pymongo.AsyncMongoClient")

        result = await mongo.get_mongo_client()

        assert result == existing_client
        mock_client_cls.assert_not_called()

    def test_get_db(self, mocker: mock.MagicMock) -> None:
        mock_client = mocker.MagicMock()
        mock_db = mocker.Mock()
        mock_client.get_database.return_value = mock_db

        result = mongo.get_db(mock_client)
        assert result == mock_db
        mock_client.get_database.assert_called_once_with(
            app_config.config.mongo_database
        )

        result2 = mongo.get_db(mock_client)
        assert result2 == mock_db
        assert mock_client.get_database.call_count == 1
