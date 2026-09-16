import logging

from app.common.log_utils import EndpointFilter, ExtraFieldsFilter


def test_extra_fields_filter_with_all_context(mocker):
    # Mock the context variables
    mock_trace_id = mocker.patch("app.common.log_utils.ctx_trace_id")
    mock_request = mocker.patch("app.common.log_utils.ctx_request")
    mock_response = mocker.patch("app.common.log_utils.ctx_response")

    # Set context values
    mock_trace_id.get.return_value = "test-trace-id"
    mock_request.get.return_value = {"url": "http://test.com", "method": "GET"}
    mock_response.get.return_value = {"status_code": 200}

    # Create a log record
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="test message",
        args=(),
        exc_info=None,
    )

    # Apply filter
    log_filter = ExtraFieldsFilter()
    result = log_filter.filter(record)

    # Assertions
    assert result is True
    assert record.trace == {"id": "test-trace-id"}
    assert record.url == {"full": "http://test.com"}
    assert record.http == {
        "request": {"method": "GET"},
        "response": {"status_code": 200},
    }


def test_extra_fields_filter_with_no_context(mocker):
    # Mock the context variables to return None/empty
    mock_trace_id = mocker.patch("app.common.log_utils.ctx_trace_id")
    mock_request = mocker.patch("app.common.log_utils.ctx_request")
    mock_response = mocker.patch("app.common.log_utils.ctx_response")

    mock_trace_id.get.return_value = None
    mock_request.get.return_value = None
    mock_response.get.return_value = None

    # Create a log record
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="test message",
        args=(),
        exc_info=None,
    )

    # Apply filter
    log_filter = ExtraFieldsFilter()
    result = log_filter.filter(record)

    # Assertions
    assert result is True
    assert not hasattr(record, "trace")
    assert not hasattr(record, "url")
    assert not hasattr(record, "http")


def test_endpoint_filter_blocks_matching_path():
    filter_path = "/health"
    log_filter = EndpointFilter(path=filter_path)

    # Create a log record containing the path
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


def test_endpoint_filter_allows_non_matching_path():
    filter_path = "/health"
    log_filter = EndpointFilter(path=filter_path)

    # Create a log record NOT containing the path
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
