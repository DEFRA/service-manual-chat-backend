import logging
import typing

from app.common.tracing import ctx_request, ctx_response, ctx_trace_id


# Adds additional ECS fields to the logger.
class ExtraFieldsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        trace_id = ctx_trace_id.get("")
        req = ctx_request.get(None)
        resp = ctx_response.get(None)

        if trace_id:
            record.__dict__["trace"] = {"id": trace_id}

        http: dict[str, typing.Any] = {}
        if req:
            record.__dict__["url"] = {"full": req.get("url", None)}
            http["request"] = {"method": req.get("method", None)}
        if resp:
            http["response"] = resp
        if http:
            record.__dict__["http"] = http
        return True


class EndpointFilter(logging.Filter):
    def __init__(self, path: str, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self._path = path

    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find(self._path) == -1
