import contextvars
from logging import getLogger

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app import config

logger = getLogger(__name__)

ctx_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id")
ctx_request: contextvars.ContextVar[dict[str, str]] = contextvars.ContextVar("request")
ctx_response: contextvars.ContextVar[dict[str, int]] = contextvars.ContextVar(
    "response"
)


# Inbound HTTP requests on the platform will have a `x-cdp-request-id` header.
# This can be used to follow a single request across multiple services.
# TraceIdMiddleware handles extracting the tracing header and persisting it
# for the duration of the request in the ContextVar `ctx_trace_id`.
class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        req_trace_id = request.headers.get(config.config.tracing_header, None)
        if req_trace_id:
            ctx_trace_id.set(req_trace_id)

        ctx_request.set({"url": str(request.url), "method": request.method})

        response = await call_next(request)
        ctx_response.set({"status_code": response.status_code})
        return response
