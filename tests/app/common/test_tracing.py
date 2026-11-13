from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.common import tracing


def test_middleware_records_status_code_and_response_time_in_ms(
    mocker: MockerFixture,
) -> None:
    mock_response = mocker.patch("app.common.tracing.ctx_response")
    mocker.patch("app.common.tracing.perf_counter", side_effect=[10.0, 10.25])

    app = FastAPI()
    app.add_middleware(tracing.TraceIdMiddleware)

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"ok": "yes"}

    TestClient(app).get("/ping")

    mock_response.set.assert_called_once_with(
        {"status_code": 200, "response_time": 250}
    )
