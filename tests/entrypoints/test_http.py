import os
import pathlib

import fastapi.testclient
import pydantic
import pytest
import pytest_mock

from app import config as app_config
from app.entrypoints import http as entrypoint


class TestLifespan:
    def test_the_mongo_client_is_opened_on_startup_and_closed_on_shutdown(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        mock_mongo_client = mocker.AsyncMock()
        mock_get_mongo = mocker.patch(
            "app.entrypoints.http.mongo.get_mongo_client",
            return_value=mock_mongo_client,
        )

        with fastapi.testclient.TestClient(entrypoint.create_app()):
            mock_get_mongo.assert_called_once()

        mock_mongo_client.close.assert_awaited_once()


class TestRoot:
    def test_the_root_path_is_not_served(self) -> None:
        # No `with`, so the lifespan (and Mongo) never starts.
        client = fastapi.testclient.TestClient(entrypoint.create_app())

        assert client.get("/").status_code == 404


class TestLogContent:
    def test_it_names_the_ref_and_page_count(
        self, tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        (tmp_path / "ai-toolkit.md").write_text("---\ntitle: AI toolkit\n---\nHome\n")
        (tmp_path / "REF").write_text("caefc03\n")
        cfg = app_config.AppConfig(content_dir=str(tmp_path))

        with caplog.at_level("INFO", logger="app.entrypoints.http"):
            entrypoint.log_content(cfg)

        assert f"toolkit content dir={tmp_path} ref=caefc03 pages=1" in caplog.text

    def test_it_says_mounted_without_a_ref(
        self, tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        cfg = app_config.AppConfig(content_dir=str(tmp_path))

        with caplog.at_level("INFO", logger="app.entrypoints.http"):
            entrypoint.log_content(cfg)

        assert "ref=mounted pages=0" in caplog.text


class TestMainProxy:
    def test_the_configured_proxy_is_exported_to_the_environment(
        self, mocker: pytest_mock.MockerFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mocker.patch("app.entrypoints.http.uvicorn.run")
        monkeypatch.delenv("HTTP_PROXY", raising=False)
        monkeypatch.delenv("HTTPS_PROXY", raising=False)
        monkeypatch.setattr(
            entrypoint.app_config,
            "config",
            app_config.AppConfig(
                http_proxy=pydantic.HttpUrl("http://proxy:8080"), log_config=None
            ),
        )

        entrypoint.main()

        assert os.environ.get("HTTP_PROXY") == "http://proxy:8080/"
        assert os.environ.get("HTTPS_PROXY") == "http://proxy:8080/"

    def test_no_proxy_in_config_leaves_the_environment_clear(
        self, mocker: pytest_mock.MockerFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mocker.patch("app.entrypoints.http.uvicorn.run")
        monkeypatch.setenv("HTTP_PROXY", "http://stale:1")
        monkeypatch.setenv("HTTPS_PROXY", "http://stale:1")
        monkeypatch.setattr(
            entrypoint.app_config,
            "config",
            app_config.AppConfig(http_proxy=None, log_config=None),
        )

        entrypoint.main()

        assert os.environ.get("HTTP_PROXY") is None
        assert os.environ.get("HTTPS_PROXY") is None
