import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

import app.entrypoints.fastapi as main_mod

client = TestClient(main_mod.app)


def test_lifespan(mocker: MockerFixture) -> None:
    mock_mongo_client = mocker.AsyncMock()
    mock_get_mongo = mocker.patch(
        "app.common.mongo.get_mongo_client", return_value=mock_mongo_client
    )

    # Using TestClient as a context manager triggers lifespan startup/shutdown
    with TestClient(main_mod.app):
        mock_get_mongo.assert_called_once()  # Startup: connect called

    mock_mongo_client.close.assert_awaited_once()  # Shutdown: close called


def test_lifespan_ensures_the_ask_daily_usage_index_for_the_bedrock_engine(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_mongo_client = mocker.AsyncMock()
    mocker.patch("app.common.mongo.get_mongo_client", return_value=mock_mongo_client)
    monkeypatch.setattr(main_mod.config.config, "ask_engine", "bedrock")
    mock_ensure = mocker.patch(
        "app.ask.bedrock.ensure_ask_daily_usage_index", return_value=None
    )

    with TestClient(main_mod.app):
        pass

    mock_ensure.assert_awaited_once()


def test_lifespan_skips_the_index_for_the_stub_engine(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_mongo_client = mocker.AsyncMock()
    mocker.patch("app.common.mongo.get_mongo_client", return_value=mock_mongo_client)
    monkeypatch.setattr(main_mod.config.config, "ask_engine", "stub")
    mock_ensure = mocker.patch(
        "app.ask.bedrock.ensure_ask_daily_usage_index", return_value=None
    )

    with TestClient(main_mod.app):
        pass

    mock_ensure.assert_not_called()


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 404


def test_main_sets_proxy_envs(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    mocker.patch("app.entrypoints.fastapi.uvicorn.run")

    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)

    monkeypatch.setattr(main_mod.config.config, "http_proxy", "http://proxy:8080")
    monkeypatch.setattr(main_mod.config.config, "host", "127.0.0.1")
    monkeypatch.setattr(main_mod.config.config, "port", 9000)
    monkeypatch.setattr(main_mod.config.config, "log_config", None)
    monkeypatch.setattr(main_mod.config.config, "python_env", "production")

    main_mod.main()

    assert os.environ.get("HTTP_PROXY") == "http://proxy:8080"
    assert os.environ.get("HTTPS_PROXY") == "http://proxy:8080"


def test_main_no_proxy_in_config(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    mocker.patch("app.entrypoints.fastapi.uvicorn.run")

    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)

    monkeypatch.setattr(main_mod.config.config, "http_proxy", None)
    monkeypatch.setattr(main_mod.config.config, "host", "127.0.0.1")
    monkeypatch.setattr(main_mod.config.config, "port", 8086)
    monkeypatch.setattr(main_mod.config.config, "log_config", None)
    monkeypatch.setattr(main_mod.config.config, "python_env", "production")

    main_mod.main()

    assert os.environ.get("HTTP_PROXY") is None
    assert os.environ.get("HTTPS_PROXY") is None


def test_log_content_names_the_ref_and_page_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    (tmp_path / "ai-toolkit.md").write_text("---\ntitle: AI toolkit\n---\nHome\n")
    (tmp_path / "REF").write_text("caefc03\n")
    monkeypatch.setattr(main_mod.config.config, "content_dir", str(tmp_path))

    with caplog.at_level("INFO", logger="app.entrypoints.fastapi"):
        main_mod.log_content()

    assert f"toolkit content dir={tmp_path} ref=caefc03 pages=1" in caplog.text


def test_log_content_says_mounted_without_a_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(main_mod.config.config, "content_dir", str(tmp_path))

    with caplog.at_level("INFO", logger="app.entrypoints.fastapi"):
        main_mod.log_content()

    assert "ref=mounted pages=0" in caplog.text
