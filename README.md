# IoT Dashboard Spoofer (IoTSpooferV0)

Secure FastAPI + web UI app for emulating IoT sensors and validating both HTTP ingestion and Mosquitto MQTT broker integrations.

## Major Feature Log (newest last)

- `work`: Added full Mosquitto-first workflow: broker connectivity testing, publish/subscribe smoke tests, sensor enrollment to topics, and telemetry emission over MQTT.

## Core Features

- Device simulation for door sensor, thermometer, camera, and switch.
- Secure request validation via Pydantic.
- HTTP forwarding checks + receipts for delivery troubleshooting.
- **MQTT workflow**:
  - Test broker connection (`/api/mqtt/connect`)
  - Publish test message (`/api/mqtt/publish`)
  - Subscribe-once test (`/api/mqtt/subscribe`)
  - Enroll simulated sensor to topic (`/api/mqtt/enroll`)
  - Emit generated sensor payload to enrolled topic (`/api/devices/{id}/emit/mqtt`)
- Debug console in UI for transparent operator feedback.

## Project Structure

```text
app/
  config.py
  main.py
  models.py
  services/
    dispatcher.py
    mqtt_service.py
    simulator.py
frontend/
  index.html
  app.js
  styles.css
tests/
  test_simulator.py
  test_mqtt_service.py
scripts/
  start_dev.sh
  start_dev.ps1
```

## Setup (Windows, Linux, macOS, Raspberry Pi)

1) Clone and enter project:

```bash
git clone <your-repo-url>
cd IoTSpooferV0
```

2) Create env file:

```bash
cp .env.example .env
```

3) Start locally:

### Linux / macOS / Raspberry Pi

```bash
bash scripts/start_dev.sh 8000
```

### Windows (PowerShell)

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
./scripts/start_dev.ps1 -Port 8000
```

Open `http://localhost:8000`.

## MQTT Quick Test (Mosquitto)

1. Start mosquitto broker (default `localhost:1883`).
2. In UI, configure broker host/port/client id.
3. Click **Test MQTT Connection**.
4. Set topic and click **Publish Test Message**.
5. Click **Subscribe Once** from another message producer window/session.
6. Enroll your selected device to a topic.
7. Click **Emit Sensor Telemetry via MQTT**.

## Deployment

- Render blueprint included via `render.yaml`.
- For production hardening, place behind TLS reverse proxy (Nginx/Caddy), set restrictive CORS, and use authenticated MQTT accounts.

## Security Notes

- No hardcoded credentials.
- TLS option supported for broker connections.
- Validation + bounded timeouts on HTTP and MQTT operations.

## Roadmap

### User-facing

- [x] Multi-device spoofing UI
- [x] HTTP forwarding + delivery receipts
- [x] MQTT connect/pub/sub tooling
- [x] Sensor enrollment to MQTT topics
- [ ] MQTT retained message manager UI
- [ ] Per-device scheduling/interval controls

### Backend / engineering

- [x] Structured services for simulator/dispatcher/mqtt
- [x] Unit tests for simulator and MQTT enrollment state
- [ ] Persistent storage for device/enrollment state
- [ ] Integration tests against containerized Mosquitto
- [ ] Role-based authentication and admin panel
