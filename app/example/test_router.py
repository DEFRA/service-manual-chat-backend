from fastapi.testclient import TestClient

from app.common.http_client import create_async_client
from app.common.mongo import get_db
from app.main import app

client = TestClient(app)


def test_root_success():
    response = client.get("/example/test")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_db_query_success(mocker):
    mock_db = mocker.AsyncMock()
    mock_db.example.insert_one.return_value = None
    mock_db.example.find_one.return_value = {"foo": "bar", "id": 123}

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.get("/example/db")

        assert response.status_code == 200
        assert response.json() == {"ok": {"foo": "bar", "id": 123}}

        mock_db.example.insert_one.assert_called_once()
    finally:
        app.dependency_overrides = {}


def test_http_query_success(mocker):
    mock_client = mocker.AsyncMock()
    mock_client.get.return_value.status_code = 200

    app.dependency_overrides[create_async_client] = lambda: mock_client

    try:
        response = client.get("/example/http")

        assert response.status_code == 200
        assert response.json() == {"ok": 200}
    finally:
        app.dependency_overrides = {}
