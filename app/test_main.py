import os

from fastapi.testclient import TestClient

import app.main as main_mod

from .main import app

client = TestClient(app)


def test_lifespan(mocker):
    mock_mongo_client = mocker.AsyncMock()
    mock_get_mongo = mocker.patch(
        "app.main.get_mongo_client", return_value=mock_mongo_client
    )

    # Using TestClient as a context manager triggers lifespan startup/shutdown
    with TestClient(app):
        mock_get_mongo.assert_called_once()  # Startup: connect called

    mock_mongo_client.close.assert_awaited_once()  # Shutdown: close called


def test_example():
    response = client.get("/example/test")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root():
    response = client.get("/")
    assert response.status_code == 404


def test_main_sets_proxy_envs(mocker, monkeypatch):
    mocker.patch("app.main.uvicorn.run")

    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)

    monkeypatch.setattr(main_mod.config, "http_proxy", "http://proxy:8080")
    monkeypatch.setattr(main_mod.config, "host", "127.0.0.1")
    monkeypatch.setattr(main_mod.config, "port", 9000)
    monkeypatch.setattr(main_mod.config, "log_config", None)
    monkeypatch.setattr(main_mod.config, "python_env", "production")

    main_mod.main()

    assert os.environ.get("HTTP_PROXY") == "http://proxy:8080"
    assert os.environ.get("HTTPS_PROXY") == "http://proxy:8080"


def test_main_no_proxy_in_config(mocker, monkeypatch):
    mocker.patch("app.main.uvicorn.run")

    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)

    monkeypatch.setattr(main_mod.config, "http_proxy", None)
    monkeypatch.setattr(main_mod.config, "host", "127.0.0.1")
    monkeypatch.setattr(main_mod.config, "port", 8086)
    monkeypatch.setattr(main_mod.config, "log_config", None)
    monkeypatch.setattr(main_mod.config, "python_env", "production")

    main_mod.main()

    assert os.environ.get("HTTP_PROXY") is None
    assert os.environ.get("HTTPS_PROXY") is None
