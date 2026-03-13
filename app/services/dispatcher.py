"""Dispatcher service for forwarding synthetic telemetry.

Purpose:
- Deliver generated events to a dashboard-under-test endpoint.
- Add robust timeout/error handling with clear debug responses.
- Persist recent forwarding receipts for endpoint verification/debugging.

Structure:
- `DispatcherService` async HTTP forwarder using httpx.
- In-memory bounded receipt log for recently attempted sends.
"""

from __future__ import annotations

import logging
from collections import deque

import httpx

from app.models import DashboardTarget, DispatchReceipt, DispatchResult, EndpointCheckResult, TelemetryEvent

logger = logging.getLogger(__name__)


class DispatcherService:
    """Sends telemetry to remote HTTP targets with hardened defaults."""

    def __init__(self, max_receipts: int = 200) -> None:
        self._receipts: deque[DispatchReceipt] = deque(maxlen=max_receipts)

    def list_receipts(self, endpoint_url: str | None = None, limit: int = 20) -> list[DispatchReceipt]:
        """Return recent forwarding receipts for debugging delivery behavior."""
        safe_limit = max(1, min(limit, 100))
        receipts = list(self._receipts)
        if endpoint_url:
            receipts = [receipt for receipt in receipts if receipt.endpoint_url == endpoint_url]
        # Newest first so UI can quickly show latest activity.
        return list(reversed(receipts))[:safe_limit]

    async def check_endpoint(self, target: DashboardTarget) -> EndpointCheckResult:
        """Probe endpoint with a lightweight request to verify service is listening."""
        headers = {"Accept": "application/json"}
        if target.auth_header_value:
            headers["Authorization"] = target.auth_header_value

        try:
            async with httpx.AsyncClient(timeout=target.timeout_seconds, follow_redirects=False) as client:
                response = await client.get(str(target.endpoint_url), headers=headers)
            # Any valid HTTP response implies network path + listener are functioning.
            return EndpointCheckResult(
                listening=True,
                status_code=response.status_code,
                message=f"Endpoint reachable (HTTP {response.status_code})",
            )
        except httpx.HTTPError as exc:
            logger.warning("endpoint_check_failed endpoint=%s error=%s", target.endpoint_url, exc)
            return EndpointCheckResult(listening=False, message=f"Endpoint check failed: {exc}")

    def _record_receipt(self, receipt: DispatchReceipt) -> None:
        self._receipts.append(receipt)

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
            result = DispatchResult(
                accepted=True,
                forwarded=ok,
                status_code=response.status_code,
                message=message,
                payload=payload,
            )
            self._record_receipt(
                DispatchReceipt(
                    endpoint_url=str(target.endpoint_url),
                    device_id=payload.device_id,
                    forwarded=ok,
                    status_code=response.status_code,
                    message=message,
                )
            )
            return result
        except httpx.HTTPError as exc:
            logger.warning("forward_error device_id=%s error=%s", payload.device_id, exc)
            message = f"Forward failed: {exc}"
            self._record_receipt(
                DispatchReceipt(
                    endpoint_url=str(target.endpoint_url),
                    device_id=payload.device_id,
                    forwarded=False,
                    message=message,
                )
            )
            return DispatchResult(
                accepted=True,
                forwarded=False,
                message=message,
                payload=payload,
            )
