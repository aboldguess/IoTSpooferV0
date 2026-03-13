"""Dispatcher service for forwarding synthetic telemetry.

Purpose:
- Deliver generated events to a dashboard-under-test endpoint.
- Add robust timeout/error handling with clear debug responses.

Structure:
- `DispatcherService` async HTTP forwarder using httpx.
"""

from __future__ import annotations

import logging

import httpx

from app.models import DashboardTarget, DispatchResult, TelemetryEvent

logger = logging.getLogger(__name__)


class DispatcherService:
    """Sends telemetry to remote HTTP targets with hardened defaults."""

    async def forward(self, payload: TelemetryEvent, target: DashboardTarget) -> DispatchResult:
        headers = {"Content-Type": "application/json"}
        if target.auth_header_value:
            headers["Authorization"] = target.auth_header_value

        try:
            async with httpx.AsyncClient(timeout=target.timeout_seconds, follow_redirects=False) as client:
                response = await client.post(str(target.endpoint_url), json=payload.model_dump(), headers=headers)

            ok = 200 <= response.status_code < 300
            message = "Forwarded successfully" if ok else f"Dashboard returned {response.status_code}"
            logger.info("forward_result status=%s device_id=%s", response.status_code, payload.device_id)
            return DispatchResult(
                accepted=True,
                forwarded=ok,
                status_code=response.status_code,
                message=message,
                payload=payload,
            )
        except httpx.HTTPError as exc:
            logger.warning("forward_error device_id=%s error=%s", payload.device_id, exc)
            return DispatchResult(
                accepted=True,
                forwarded=False,
                message=f"Forward failed: {exc}",
                payload=payload,
            )
