import logging
import time
from uuid import uuid4

from fastapi import Request

logger = logging.getLogger("smart_merchant.requests")


async def request_middleware(request: Request, call_next):
    request.state.request_id = str(uuid4())
    start = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    logger.info(
        "request",
        extra={
            "request_id": request.state.request_id,
            "method": request.method,
            "route": request.url.path,
            "status": response.status_code,
            "duration_ms": round((time.monotonic() - start) * 1000, 2),
        },
    )
    return response
