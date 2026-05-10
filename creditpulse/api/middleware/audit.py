from __future__ import annotations

import time
import uuid
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from creditpulse.db.models import AuditLog
from creditpulse.db.session import AsyncSessionLocal
from creditpulse.logging_config import get_logger

logger = get_logger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)
        latency_ms = int((time.perf_counter() - start) * 1000)

        if not request.url.path.startswith("/v1/"):
            return response

        lender_id_str: Optional[str] = getattr(request.state, "lender_id", None)
        lender_uuid: Optional[uuid.UUID] = None
        if lender_id_str:
            try:
                lender_uuid = uuid.UUID(lender_id_str)
            except ValueError:
                lender_uuid = None

        client_host = request.client.host if request.client else None

        try:
            async with AsyncSessionLocal() as session:
                log = AuditLog(
                    lender_id=lender_uuid,
                    endpoint=request.url.path,
                    method=request.method,
                    request_summary={
                        "query": dict(request.query_params),
                        "path": request.url.path,
                    },
                    response_code=response.status_code,
                    latency_ms=latency_ms,
                    ip_address=client_host,
                )
                session.add(log)
                await session.commit()
        except Exception as exc:
            logger.warning("audit_write_failed", error=str(exc))

        response.headers["X-Processing-Ms"] = str(latency_ms)
        return response
