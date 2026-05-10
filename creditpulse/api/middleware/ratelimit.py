from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from creditpulse.config import get_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, per_minute: int | None = None):
        super().__init__(app)
        self.per_minute = per_minute or get_settings().rate_limit_per_minute
        self.buckets: Dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith("/v1/"):
            return await call_next(request)

        key = request.headers.get("X-API-Key") or (request.client.host if request.client else "anon")
        now = time.time()
        bucket = self.buckets[key]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()

        if len(bucket) >= self.per_minute:
            retry_after = int(60 - (now - bucket[0])) if bucket else 60
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(max(1, retry_after))},
            )

        bucket.append(now)
        return await call_next(request)
