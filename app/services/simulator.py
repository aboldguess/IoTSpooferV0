"""Simulation service for generating synthetic IoT telemetry.

Purpose:
- Create realistic-but-safe payloads for common device archetypes.
- Keep deterministic business logic isolated from HTTP routes.

Structure:
- `DeviceRuntimeState` for mutable simulation state.
- `SimulatorService` to register/update devices and emit telemetry.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models import DeviceCommand, DeviceProfile, DeviceType, TelemetryEvent


@dataclass
class DeviceRuntimeState:
    """In-memory state for one emulated device."""

    profile: DeviceProfile
    switch_state: bool = False
    switch_level: int = 50
    last_camera_data_url: str | None = None
    sequence: int = 0
    recent_temps: list[float] = field(default_factory=list)


class SimulatorService:
    """Generates telemetry for supported virtual device families."""

    def __init__(self) -> None:
        self._devices: dict[str, DeviceRuntimeState] = {}

    def upsert_device(self, profile: DeviceProfile) -> DeviceRuntimeState:
        existing = self._devices.get(profile.id)
        if existing:
            existing.profile = profile
            return existing

        state = DeviceRuntimeState(profile=profile)
        self._devices[profile.id] = state
        return state

    def list_devices(self) -> list[DeviceRuntimeState]:
        return list(self._devices.values())

    def update_command(self, device_id: str, command: DeviceCommand) -> DeviceRuntimeState:
        state = self._devices[device_id]
        if command.switch_state is not None:
            state.switch_state = command.switch_state
        if command.switch_level is not None:
            state.switch_level = command.switch_level
        return state

    def update_camera_frame(self, device_id: str, data_url: str) -> DeviceRuntimeState:
        state = self._devices[device_id]
        state.last_camera_data_url = data_url
        return state

    def generate_event(self, device_id: str) -> TelemetryEvent:
        state = self._devices[device_id]
        profile = state.profile
        state.sequence += 1

        readings = self._build_readings(state)
        debug = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sequence": state.sequence,
        }

        return TelemetryEvent(
            device_id=profile.id,
            device_name=profile.device_name,
            device_type=profile.device_type,
            serial_number=profile.serial_number,
            battery_voltage=profile.battery_voltage,
            signal_strength_dbm=profile.signal_strength_dbm,
            readings=readings,
            debug=debug,
        )

    def _build_readings(self, state: DeviceRuntimeState) -> dict:
        profile = state.profile

        if profile.device_type == DeviceType.door_sensor:
            return {
                "door_closed": random.choice([True, False]),
                "tamper_detected": random.choice([False, False, True]),
                "network": "NB-IoT",
            }

        if profile.device_type == DeviceType.thermometer:
            temp = round(random.uniform(16.0, 30.0), 2)
            state.recent_temps = (state.recent_temps + [temp])[-10:]
            avg = round(sum(state.recent_temps) / len(state.recent_temps), 2)
            return {
                "temperature_c": temp,
                "rolling_avg_c": avg,
                "host": "raspberry-pi",
            }

        if profile.device_type == DeviceType.camera:
            return {
                "motion_detected": random.choice([False, True]),
                "image_data_url": state.last_camera_data_url,
                "encoding": "base64_data_url",
            }

        if profile.device_type == DeviceType.switch:
            return {
                "switch_on": state.switch_state,
                "level": state.switch_level,
                "mode": "manual_override",
            }

        return {"status": "unknown_device_type"}
