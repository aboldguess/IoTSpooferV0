"""Data models for the IoT spoofing platform.

Purpose:
- Define strongly typed request/response objects.
- Keep payload validation and schema generation in one place.

Structure:
- Enum values for device categories.
- Device profile/config models.
- Telemetry event and dispatch response models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class DeviceType(str, Enum):
    door_sensor = "nb_iot_door_sensor"
    thermometer = "raspberry_pi_thermometer"
    camera = "iot_camera"
    switch = "iot_switch"


class DeviceProfile(BaseModel):
    """Represents an emulated IoT device identity."""

    id: str = Field(..., min_length=3, max_length=64)
    device_name: str = Field(..., min_length=3, max_length=120)
    device_type: DeviceType
    serial_number: str = Field(..., min_length=3, max_length=120)
    firmware_version: str = Field(default="1.0.0", min_length=1, max_length=30)
    battery_voltage: float = Field(default=3.7, ge=2.5, le=5.5)
    signal_strength_dbm: int = Field(default=-75, ge=-140, le=-40)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DashboardTarget(BaseModel):
    """Target endpoint for forwarding synthetic telemetry."""

    endpoint_url: HttpUrl
    auth_header_value: str | None = Field(default=None, max_length=500)
    timeout_seconds: int = Field(default=8, ge=1, le=30)


class DeviceCommand(BaseModel):
    """Command model for toggles/scales applied to a simulated device."""

    switch_state: bool | None = None
    switch_level: int | None = Field(default=None, ge=1, le=100)


class TelemetryEvent(BaseModel):
    """Generated telemetry payload for a single synthetic reading."""

    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    device_id: str
    device_name: str
    device_type: DeviceType
    serial_number: str
    battery_voltage: float
    signal_strength_dbm: int
    readings: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)


class CameraUploadRequest(BaseModel):
    """Client camera snapshot used to emulate an IoT camera event."""

    data_url: str = Field(..., min_length=20)

    @field_validator("data_url")
    @classmethod
    def ensure_base64_data_url(cls, value: str) -> str:
        if not value.startswith("data:image/"):
            raise ValueError("Expected a data URL beginning with data:image/")
        if ";base64," not in value:
            raise ValueError("Expected base64 encoded image data")
        return value


class DispatchResult(BaseModel):
    """Delivery status for local generation and optional dashboard forwarding."""

    accepted: bool
    forwarded: bool
    status_code: int | None = None
    message: str
    payload: TelemetryEvent
