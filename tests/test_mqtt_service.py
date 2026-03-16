"""Tests for MQTT service state and enrollment behavior.

Purpose:
- Verify enrollment CRUD flows used by MQTT publishing workflows.
- Keep MQTT mapping logic deterministic without requiring a live broker.
"""

from app.models import SensorEnrollment
from app.services.mqtt_service import MqttService


def test_upsert_and_get_enrollment() -> None:
    service = MqttService()
    enrollment = SensorEnrollment(device_id="dev-1", topic="sensors/dev-1", qos=1)

    saved = service.upsert_enrollment(enrollment)

    assert saved.device_id == "dev-1"
    assert service.get_enrollment("dev-1") is not None
    assert service.get_enrollment("dev-1").topic == "sensors/dev-1"


def test_list_enrollments_returns_all_items() -> None:
    service = MqttService()
    service.upsert_enrollment(SensorEnrollment(device_id="dev-1", topic="sensors/dev-1"))
    service.upsert_enrollment(SensorEnrollment(device_id="dev-2", topic="sensors/dev-2"))

    enrollments = service.list_enrollments()

    assert len(enrollments) == 2
    assert {item.device_id for item in enrollments} == {"dev-1", "dev-2"}
