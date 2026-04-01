"""
core/middleware.py
──────────────────
AuditMiddleware: auto-logs all mutating requests to audit_logs.
RateLimitMiddleware: Redis-backed sliding window rate limiter.
"""
import time
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

log = structlog.get_logger()

MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 60  # seconds


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Logs all mutating requests (POST/PUT/PATCH/DELETE) to structlog.
    The audit module's use_cases write to the DB — this just captures the HTTP layer.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        if request.method in MUTATION_METHODS:
            employee_id = getattr(request.state, "employee_id", None)
            log.info(
                "http.mutation",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                employee_id=str(employee_id) if employee_id else None,
                ip=request.client.host if request.client else None,
            )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter using Redis.
    100 requests / 60 seconds per IP. Skips health checks.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in ("/health", "/metrics"):
            return await call_next(request)

        from app.core.config import settings
        from redis.asyncio import Redis

        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}"

        try:
            pipe = redis.pipeline()
            now = int(time.time())
            window_start = now - RATE_LIMIT_WINDOW

            # Sliding window: remove old entries, add current, count
            await pipe.zremrangebyscore(key, 0, window_start)
            await pipe.zadd(key, {str(now): now})
            await pipe.zcard(key)
            await pipe.expire(key, RATE_LIMIT_WINDOW)
            results = await pipe.execute()

            request_count = results[2]
            if request_count > RATE_LIMIT_REQUESTS:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests. Please slow down.",
                            "field": None,
                        },
                    },
                    headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
                )
        except Exception:
            pass  # Redis down → don't block requests
        finally:
            await redis.aclose()

        return await call_next(request)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attaches request-level context (correlation ID, timing) to request.state."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        import uuid
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response