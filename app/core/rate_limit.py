"""Per-IP rate limiting for the coach.

The coach is the one endpoint in the stack where an abusive caller costs real
money: every request reaches the Anthropic API. The backend's own limiter
does not cover this service — it sits behind nginx on a different path prefix
and never goes through the backend process — so it needs its own.

Sliding window per IP, in memory. That is enough for a single instance; with
several replicas each keeps its own counters, which means the effective limit
is multiplied by the replica count. Set COACH_RATE_LIMIT_PER_MINUTE lower if
you scale out, or put a shared limiter in front.
"""
import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.config import RATE_LIMIT_PER_MINUTE

WINDOW_SECONDS = 60


class CoachRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = RATE_LIMIT_PER_MINUTE) -> None:
        super().__init__(app)
        self.limit = limit
        self._hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if self.limit <= 0 or request.url.path == "/health":
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        now = time.time()
        window = self._hits[client]
        while window and now - window[0] > WINDOW_SECONDS:
            window.popleft()

        if len(window) >= self.limit:
            retry_after = int(WINDOW_SECONDS - (now - window[0])) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        "Too many coach requests. Give it a minute and try again."
                    )
                },
                headers={"Retry-After": str(retry_after)},
            )

        window.append(now)

        # Keep the map from growing without bound on a busy or hostile host.
        if len(self._hits) > 10_000:
            self._hits = {
                key: hits
                for key, hits in self._hits.items()
                if hits and now - hits[0] <= WINDOW_SECONDS
            }

        return await call_next(request)
