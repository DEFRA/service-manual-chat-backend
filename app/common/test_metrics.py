from app.common.metrics import counter


def test_counter_success(mocker):
    mock_put_metric = mocker.patch("app.common.metrics.__put_metric")

    counter("test_metric", 123)

    mock_put_metric.assert_called_once_with("test_metric", 123, "Count")


def test_counter_handles_exception(mocker):
    mocker.patch("app.common.metrics.__put_metric", side_effect=Exception("Test Error"))
    mock_logger = mocker.patch("app.common.metrics.logger")

    # Should not raise exception but catch it
    counter("test_metric", 123)

    # Verify error was logged
    assert mock_logger.error.call_count == 1
    args, _ = mock_logger.error.call_args
    assert "Error calling put_metric" in args[0]
    assert str(args[1]) == "Test Error"
