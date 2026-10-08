import logging
import typing

from app.common import tracing


# Adds additional ECS fields to the logger.
class ExtraFieldsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        trace_id = tracing.ctx_trace_id.get("")
        req = tracing.ctx_request.get(None)
        resp = tracing.ctx_response.get(None)

        if trace_id:
            record.trace = {"id": trace_id}  # type: ignore[attr-defined]

        http: dict[str, typing.Any] = {}
        if req:
            record.url = {"full": req.get("url", None)}  # type: ignore[attr-defined]
            http["request"] = {"method": req.get("method", None)}
        if resp:
            http["response"] = resp
        if http:
            record.http = http  # type: ignore[attr-defined]
        return True


class EndpointFilter(logging.Filter):
    def __init__(self, path: str, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self._path = path

    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find(self._path) == -1
