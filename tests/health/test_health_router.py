import fastapi.testclient


class TestHealthEndpoint:
    def test_health_endpoint_returns_ok(
        self, client: fastapi.testclient.TestClient
    ) -> None:
        response = client.get("/health")

        assert response.status_code == 200

        assert response.json() == {"status": "ok"}
