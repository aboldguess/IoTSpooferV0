"""MQTT service abstraction for broker connectivity and pub/sub validation.

Purpose:
- Provide secure, debuggable Mosquitto broker integration.
- Support connect testing, publish, and subscribe operations from API routes.

Structure:
- `MqttService` manages short-lived paho-mqtt clients for operations.
- In-memory enrollment registry tracks sensor/topic bindings.
"""

from __future__ import annotations

import json
import logging
import ssl
import threading
import uuid
from dataclasses import dataclass

import paho.mqtt.client as mqtt

from app.models import MqttActionResult, MqttBrokerConfig, MqttPublishRequest, MqttSubscribeRequest, SensorEnrollment

logger = logging.getLogger(__name__)


@dataclass
class _ConnectionState:
    connected: threading.Event
    published: threading.Event
    message_received: threading.Event
    connect_rc: int | None = None
    publish_rc: int | None = None
    inbound_topic: str | None = None
    inbound_payload: str | None = None


class MqttService:
    """Service class exposing reusable MQTT test and messaging operations."""

    def __init__(self) -> None:
        self._enrollments: dict[str, SensorEnrollment] = {}

    def list_enrollments(self) -> list[SensorEnrollment]:
        """List known sensor-to-topic enrollments."""
        return list(self._enrollments.values())

    def upsert_enrollment(self, enrollment: SensorEnrollment) -> SensorEnrollment:
        """Create/update enrollment mapping by device id."""
        self._enrollments[enrollment.device_id] = enrollment
        return enrollment

    def get_enrollment(self, device_id: str) -> SensorEnrollment | None:
        """Fetch enrollment for a specific simulated sensor."""
        return self._enrollments.get(device_id)

    def _build_client(self, config: MqttBrokerConfig, suffix: str) -> mqtt.Client:
        client_id = f"{config.client_id}-{suffix}-{uuid.uuid4().hex[:8]}"
        client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv5)
        if config.username:
            client.username_pw_set(config.username, config.password)
        if config.tls_enabled:
            # Use platform trust store by default for secure broker connections.
            client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        return client

    def test_connection(self, config: MqttBrokerConfig) -> MqttActionResult:
        """Verify broker connectivity with a short-lived client."""
        state = _ConnectionState(connected=threading.Event(), published=threading.Event(), message_received=threading.Event())
        client = self._build_client(config, "connect-test")

        def on_connect(_: mqtt.Client, __, ___, rc, *args) -> None:  # type: ignore[no-untyped-def]
            state.connect_rc = rc
            state.connected.set()

        client.on_connect = on_connect

        try:
            client.connect(config.host, config.port, config.keepalive_seconds)
            client.loop_start()
            if not state.connected.wait(timeout=5):
                return MqttActionResult(success=False, message="Connection timeout (no CONNACK from broker)")
            if state.connect_rc != 0:
                return MqttActionResult(success=False, message=f"Broker rejected connection (rc={state.connect_rc})")
            return MqttActionResult(success=True, message="Connected to MQTT broker successfully")
        except Exception as exc:  # noqa: BLE001
            logger.warning("mqtt_connection_test_failed host=%s port=%s error=%s", config.host, config.port, exc)
            return MqttActionResult(success=False, message=f"Connection failed: {exc}")
        finally:
            client.loop_stop()
            client.disconnect()

    def publish(self, config: MqttBrokerConfig, request: MqttPublishRequest) -> MqttActionResult:
        """Publish a message to a broker topic and confirm broker acceptance."""
        state = _ConnectionState(connected=threading.Event(), published=threading.Event(), message_received=threading.Event())
        client = self._build_client(config, "publish")

        def on_connect(_: mqtt.Client, __, ___, rc, *args) -> None:  # type: ignore[no-untyped-def]
            state.connect_rc = rc
            state.connected.set()

        def on_publish(_: mqtt.Client, __, mid, rc, *args) -> None:  # type: ignore[no-untyped-def]
            state.publish_rc = rc
            state.published.set()

        client.on_connect = on_connect
        client.on_publish = on_publish

        payload = request.payload if isinstance(request.payload, str) else json.dumps(request.payload)

        try:
            client.connect(config.host, config.port, config.keepalive_seconds)
            client.loop_start()
            if not state.connected.wait(timeout=5):
                return MqttActionResult(success=False, message="Publish failed: connection timeout", topic=request.topic)
            if state.connect_rc != 0:
                return MqttActionResult(success=False, message=f"Publish failed: connect rc={state.connect_rc}", topic=request.topic)

            publish_info = client.publish(request.topic, payload=payload, qos=request.qos, retain=request.retain)
            if publish_info.rc != mqtt.MQTT_ERR_SUCCESS:
                return MqttActionResult(success=False, message=f"Publish enqueue failed rc={publish_info.rc}", topic=request.topic)
            if not state.published.wait(timeout=5):
                return MqttActionResult(success=False, message="Publish timeout waiting for PUBACK/PUBCOMP", topic=request.topic)

            return MqttActionResult(success=True, message="Message published successfully", topic=request.topic, payload=request.payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("mqtt_publish_failed topic=%s error=%s", request.topic, exc)
            return MqttActionResult(success=False, message=f"Publish failed: {exc}", topic=request.topic)
        finally:
            client.loop_stop()
            client.disconnect()

    def subscribe_once(self, config: MqttBrokerConfig, request: MqttSubscribeRequest) -> MqttActionResult:
        """Subscribe and wait for one message for smoke-testing broker subscriptions."""
        state = _ConnectionState(connected=threading.Event(), published=threading.Event(), message_received=threading.Event())
        client = self._build_client(config, "subscribe")

        def on_connect(current_client: mqtt.Client, __, ___, rc, *args) -> None:  # type: ignore[no-untyped-def]
            state.connect_rc = rc
            if rc == 0:
                current_client.subscribe(request.topic, qos=request.qos)
            state.connected.set()

        def on_message(_: mqtt.Client, __, msg) -> None:  # type: ignore[no-untyped-def]
            state.inbound_topic = msg.topic
            state.inbound_payload = msg.payload.decode("utf-8", errors="replace")
            state.message_received.set()

        client.on_connect = on_connect
        client.on_message = on_message

        try:
            client.connect(config.host, config.port, config.keepalive_seconds)
            client.loop_start()
            if not state.connected.wait(timeout=5):
                return MqttActionResult(success=False, message="Subscribe failed: connection timeout", topic=request.topic)
            if state.connect_rc != 0:
                return MqttActionResult(success=False, message=f"Subscribe failed: connect rc={state.connect_rc}", topic=request.topic)
            if not state.message_received.wait(timeout=request.wait_seconds):
                return MqttActionResult(success=False, message="No message received within wait window", topic=request.topic)
            return MqttActionResult(
                success=True,
                message="Subscription test message received",
                topic=state.inbound_topic,
                payload=state.inbound_payload,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("mqtt_subscribe_failed topic=%s error=%s", request.topic, exc)
            return MqttActionResult(success=False, message=f"Subscribe failed: {exc}", topic=request.topic)
        finally:
            client.loop_stop()
            client.disconnect()
