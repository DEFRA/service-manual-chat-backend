from unittest import mock

from app.common import metrics


class TestMetrics:
    def test_counter_success(self, mocker: mock.MagicMock) -> None:
        mock_put_metric = mocker.patch("app.common.metrics.__put_metric")

        metrics.counter("test_metric", 123)

        mock_put_metric.assert_called_once_with("test_metric", 123, "Count")

    def test_counter_handles_exception(self, mocker: mock.MagicMock) -> None:
        mocker.patch(
            "app.common.metrics.__put_metric",
            side_effect=Exception("Test Error"),
        )
        mock_logger = mocker.patch("app.common.metrics.logger")

        metrics.counter("test_metric", 123)

        mock_logger.exception.assert_called_once_with("Error calling put_metric")
