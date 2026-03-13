"""Tests for simulation payload generation.

Purpose:
- Verify that each device type emits expected reading keys.
- Keep core telemetry generation behavior stable and debuggable.
"""

from app.models import DeviceProfile, DeviceType
from app.services.simulator import SimulatorService


def _base_profile(device_type: DeviceType, device_id: str = "dev-1") -> DeviceProfile:
    return DeviceProfile(
        id=device_id,
        device_name="Demo",
        device_type=device_type,
        serial_number="SN-1",
    )


def test_thermometer_payload_contains_temperature() -> None:
    service = SimulatorService()
    service.upsert_device(_base_profile(DeviceType.thermometer))
    event = service.generate_event("dev-1")
    assert "temperature_c" in event.readings
    assert "rolling_avg_c" in event.readings


def test_switch_payload_contains_level_and_state() -> None:
    service = SimulatorService()
    service.upsert_device(_base_profile(DeviceType.switch))
    event = service.generate_event("dev-1")
    assert "switch_on" in event.readings
    assert "level" in event.readings
