import logging
from unittest import mock

from app.common import log_utils


class TestExtraFieldsFilter:
    def test_filter_with_all_context(self, mocker: mock.MagicMock) -> None:
        mock_trace_id = mocker.patch("app.common.tracing.ctx_trace_id")
        mock_request = mocker.patch("app.common.tracing.ctx_request")
        mock_response = mocker.patch("app.common.tracing.ctx_response")

        mock_trace_id.get.return_value = "test-trace-id"
        mock_request.get.return_value = {
            "url": "http://test.com",
            "method": "GET",
        }
        mock_response.get.return_value = {"status_code": 200}

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="test message",
            args=(),
            exc_info=None,
        )

        log_filter = log_utils.ExtraFieldsFilter()
        result = log_filter.filter(record)

        assert result is True
        assert record.trace == {"id": "test-trace-id"}
        assert record.url == {"full": "http://test.com"}
        assert record.http == {
            "request": {"method": "GET"},
            "response": {"status_code": 200},
        }

    def test_filter_with_no_context(self, mocker: mock.MagicMock) -> None:
        mock_trace_id = mocker.patch("app.common.tracing.ctx_trace_id")
        mock_request = mocker.patch("app.common.tracing.ctx_request")
        mock_response = mocker.patch("app.common.tracing.ctx_response")

        mock_trace_id.get.return_value = None
        mock_request.get.return_value = None
        mock_response.get.return_value = None

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="test message",
            args=(),
            exc_info=None,
        )

        log_filter = log_utils.ExtraFieldsFilter()
        result = log_filter.filter(record)

        assert result is True
        assert not hasattr(record, "trace")
        assert not hasattr(record, "url")
        assert not hasattr(record, "http")


class TestEndpointFilter:
    def test_blocks_matching_path(self) -> None:
        filter_path = "/health"
        log_filter = log_utils.EndpointFilter(path=filter_path)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg=f"GET {filter_path} HTTP/1.1",
            args=(),
            exc_info=None,
        )

        assert log_filter.filter(record) is False

    def test_allows_non_matching_path(self) -> None:
        filter_path = "/health"
        log_filter = log_utils.EndpointFilter(path=filter_path)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="GET /api/users HTTP/1.1",
            args=(),
            exc_info=None,
        )

        assert log_filter.filter(record) is True
