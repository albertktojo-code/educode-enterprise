from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import defaultdict
from contextvars import ContextVar
from dataclasses import dataclass
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import get_settings

request_id_context: ContextVar[str] = ContextVar("request_id", default="")
trace_id_context: ContextVar[str] = ContextVar("trace_id", default="")
logger = logging.getLogger("educode.request")


@dataclass
class LocalRateEntry:
    count: int
    expires_at: float


_LOCAL_LIMITS: dict[str, LocalRateEntry] = defaultdict(lambda: LocalRateEntry(0, 0.0))


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        from app.services.observability import REQUEST_METRICS

        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        trace_id = request.headers.get("X-Trace-ID") or uuid4().hex
        token = request_id_context.set(request_id)
        trace_token = trace_id_context.set(trace_id)
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        started = time.perf_counter()
        exception_raised = False
        REQUEST_METRICS.begin()
        try:
            response = await call_next(request)
        except Exception:
            exception_raised = True
            logger.exception("Unhandled request failure", extra={"request_id": request_id, "trace_id": trace_id})
            response = JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Não foi possível concluir a operação.",
                        "request_id": request_id,
                    }
                },
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        duration_ms = int((time.perf_counter() - started) * 1000)
        REQUEST_METRICS.finish(request.method, request.url.path, response.status_code, duration_ms, exception=exception_raised)
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                },
                ensure_ascii=False,
            )
        )
        request_id_context.reset(token)
        trace_id_context.reset(trace_token)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )
        if not get_settings().debug:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class MaintenanceModeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        mode = "maintenance" if settings.maintenance_mode else settings.maintenance_access_mode
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            cached_mode = await redis.get(f"{settings.job_queue_prefix}:maintenance:mode")
            if cached_mode in {"available", "read_only", "maintenance"}:
                mode = cached_mode
        except RedisError:
            pass
        finally:
            await redis.aclose()
        allowed = (
            request.url.path.endswith("/health")
            or "/health/" in request.url.path
            or request.url.path.endswith("/platform/version")
            or any(
                request.url.path.endswith(suffix)
                for suffix in (
                    "/auth/login",
                    "/auth/refresh",
                    "/auth/logout",
                    "/auth/forgot-password",
                    "/auth/reset-password",
                )
            )
        )
        if mode == "maintenance" and not allowed:
            return JSONResponse(
                status_code=503,
                headers={"Retry-After": "300"},
                content={"error": {"code": "PLATFORM_MAINTENANCE", "message": "O EduCode está em manutenção programada."}},
            )
        if mode == "read_only" and not allowed and request.method not in {"GET", "HEAD", "OPTIONS"}:
            return JSONResponse(
                status_code=503,
                headers={"Retry-After": "120"},
                content={"error": {"code": "PLATFORM_READ_ONLY", "message": "O EduCode está temporariamente em modo somente leitura."}},
            )
        return await call_next(request)


def _rate_scope(path: str) -> str:
    if path.endswith("/auth/login"):
        return "auth:login"
    if path.endswith("/auth/forgot-password"):
        return "auth:forgot-password"
    if path.endswith("/auth/reset-password"):
        return "auth:reset-password"
    if path.endswith("/auth/refresh"):
        return "auth:refresh"
    if "/ai/" in path or path.endswith("/ai"):
        return "ai"
    parts = [part for part in path.strip("/").split("/") if part]
    return ":".join(parts[:3]) or "root"


def _rate_identity(request: Request) -> str:
    ip_address = request.client.host if request.client else "unknown"
    authorization = request.headers.get("authorization", "")
    if not authorization:
        return f"{ip_address}:anonymous"
    fingerprint = hashlib.sha256(authorization.encode("utf-8")).hexdigest()[:16]
    return f"{ip_address}:{fingerprint}"


def _prune_local_limits(now: float) -> None:
    if len(_LOCAL_LIMITS) < 5000:
        return
    expired = [key for key, entry in _LOCAL_LIMITS.items() if entry.expires_at <= now]
    for key in expired[:2500]:
        _LOCAL_LIMITS.pop(key, None)


def _limit_for_path(path: str) -> int:
    settings = get_settings()
    if path.endswith("/auth/login"):
        return settings.rate_limit_login_requests
    if path.endswith("/auth/forgot-password") or path.endswith("/auth/reset-password"):
        return settings.rate_limit_password_reset_requests
    if "/ai/" in path or path.endswith("/ai"):
        return settings.rate_limit_ai_requests
    return settings.rate_limit_default_requests


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == "OPTIONS" or "/health" in request.url.path:
            return await call_next(request)
        settings = get_settings()
        limit = _limit_for_path(request.url.path)
        identity = _rate_identity(request)
        rate_scope = _rate_scope(request.url.path)
        bucket = int(time.time() // settings.rate_limit_window_seconds)
        key = f"{settings.job_queue_prefix}:rate:{identity}:{rate_scope}:{bucket}"
        count = 0
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            count = int(await redis.incr(key))
            if count == 1:
                await redis.expire(key, settings.rate_limit_window_seconds + 1)
        except RedisError:
            now = time.time()
            _prune_local_limits(now)
            entry = _LOCAL_LIMITS[key]
            if entry.expires_at <= now:
                entry.count = 0
                entry.expires_at = now + settings.rate_limit_window_seconds
            entry.count += 1
            count = entry.count
        finally:
            await redis.aclose()
        if count > limit:
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(settings.rate_limit_window_seconds)},
                content={"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Muitas solicitações. Tente novamente em instantes."}},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(limit - count, 0))
        return response
