"""Structured logging and error-handling middleware."""

import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("evidence_intelligence")
logging.basicConfig(
    level=logging.INFO,
    format=(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
        '"logger": "%(name)s", "message": "%(message)s"}'
    ),
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = uuid.uuid4().hex[:12]
        start = time.monotonic()
        logger.info(
            "request_start trace_id=%s method=%s path=%s",
            trace_id,
            request.method,
            request.url.path,
        )
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.exception(
                "request_failed trace_id=%s method=%s path=%s elapsed_ms=%.1f",
                trace_id,
                request.method,
                request.url.path,
                elapsed_ms,
            )
            return JSONResponse(
                status_code=500,
                content={"error": "internal_error", "trace_id": trace_id},
            )
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "request_end trace_id=%s method=%s path=%s status=%s elapsed_ms=%.1f",
            trace_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        response.headers["X-Trace-Id"] = trace_id
        return response
