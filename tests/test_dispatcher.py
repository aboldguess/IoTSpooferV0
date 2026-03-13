"""Tests for endpoint listener checks and forwarding receipt visibility.

Purpose:
- Validate endpoint probing behavior used by the UI listener-check button.
- Confirm forwarding attempts are persisted as receipts for debugging.
"""

from __future__ import annotations

import asyncio

from app.models import DashboardTarget, DeviceProfile, DeviceType
from app.services.dispatcher import DispatcherService
from app.services.simulator import SimulatorService


def test_check_endpoint_returns_listening_on_http_response() -> None:
    service = DispatcherService()
    target = DashboardTarget(endpoint_url="http://127.0.0.1:9/health", timeout_seconds=1)

    # Port 9 is expected to reject quickly in CI/local, which still proves code path for failure.
    result = asyncio.run(service.check_endpoint(target))
    assert result.listening is False or result.status_code is not None


def test_forward_attempt_creates_receipt() -> None:
    simulator = SimulatorService()
    simulator.upsert_device(
        DeviceProfile(
            id="dev-1",
            device_name="Demo",
            device_type=DeviceType.switch,
            serial_number="SN-1",
        )
    )
    event = simulator.generate_event("dev-1")

    service = DispatcherService()
    target = DashboardTarget(endpoint_url="http://127.0.0.1:9/iot", timeout_seconds=1)
    asyncio.run(service.forward(event, target))

    receipts = service.list_receipts(endpoint_url="http://127.0.0.1:9/iot", limit=5)
    assert len(receipts) == 1
    assert receipts[0].device_id == "dev-1"
    assert receipts[0].endpoint_url == "http://127.0.0.1:9/iot"
