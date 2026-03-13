# IoT Dashboard Spoofer (IoTSpooferV0)

A secure, developer-friendly app to emulate multiple IoT device types and stress-test a dashboard ingest pipeline using spoofed device metadata and synthetic telemetry.

## What this app does

- Emulates multiple virtual IoT devices concurrently.
- Supports device archetypes:
  - NB-IoT door-close sensor
  - Raspberry Pi thermometer
  - IoT camera (using browser webcam)
  - IoT switch (on/off + 1-100 scale)
- Spoofs identity/meta fields (device name, serial number, battery voltage, signal strength, firmware).
- Lets you forward telemetry to your dashboard endpoint with optional `Authorization` header.
- Provides a browser UI with built-in usage instructions and a debug console.

---

## Security-first choices

- Input validation for all API requests via Pydantic models.
- Camera payload size cap (`MAX_CAMERA_IMAGE_BYTES`) to reduce abuse risk.
- HTTP forwarding with strict timeout and no automatic redirects.
- Config via environment variables for safer deployment.
- No hardcoded secrets.

---

## Tech stack

- **Backend:** FastAPI + Uvicorn
- **HTTP client:** httpx
- **Frontend:** Vanilla HTML/CSS/JS (easy to debug)
- **Tests:** pytest

---

## Project structure

```text
app/
  config.py              # environment-based app settings
  main.py                # FastAPI routes and static hosting
  models.py              # typed request/response schemas
  services/
    simulator.py         # telemetry simulation logic
    dispatcher.py        # HTTP forwarding to dashboard
frontend/
  index.html             # SPA UI with on-screen instructions
  app.js                 # client interactions, webcam capture, API calls
  styles.css             # modern UI styling
scripts/
  start_dev.sh           # Linux/macOS local setup and run
  start_dev.ps1          # Windows local setup and run
tests/
  test_simulator.py      # payload generation tests
render.yaml              # Render.com deployment blueprint
.env.example             # sample environment variables
requirements.txt         # dependencies
```

---

## Local setup and run (idiot-proof)

### 1) Clone

```bash
git clone <your-repo-url>
cd IoTSpooferV0
```

### 2) Create environment variables

```bash
cp .env.example .env
```

You can change `APP_PORT`, `LOG_LEVEL`, etc. in `.env`.

---

### Linux (Ubuntu/Debian etc.)

```bash
bash scripts/start_dev.sh 8000
```

Then open: `http://localhost:8000`

---

### macOS

```bash
bash scripts/start_dev.sh 8000
```

Then open: `http://localhost:8000`

---

### Windows (PowerShell)

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
./scripts/start_dev.ps1 -Port 8000
```

Then open: `http://localhost:8000`

---

### Raspberry Pi (Raspberry Pi OS)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
bash scripts/start_dev.sh 8000
```

Then open from Pi browser (or another machine on LAN):
`http://<raspberry-pi-ip>:8000`

---

## Manual run (if you prefer)

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .\.venv\Scripts\Activate.ps1  # Windows
pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production-grade server option

For production-like local run without reload:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

(For enterprise hardening, place behind Nginx/Caddy with TLS.)

---

## How to use the app

1. Open the web app.
2. In **Register / Update Device**, create your virtual device with spoofed fields.
3. In **Test Controls**, choose a device.
4. For switch devices: set on/off and level, then click **Apply Switch Command**.
5. For camera devices: click **Start Webcam**, then **Capture Frame**.
6. In **Dashboard Under Test Configuration**, add endpoint URL (and optional auth header).
7. Click **Generate & Send**.
8. Check **Debug Console** for payload and forwarding result.

---

## How to configure your dashboard under test

Most dashboards expect an HTTP ingestion endpoint. Configure it like this:

1. Create an endpoint in your dashboard/backend that accepts JSON `POST` requests.
2. Accept these fields from incoming payload:
   - `device_id`
   - `device_name`
   - `device_type`
   - `serial_number`
   - `battery_voltage`
   - `signal_strength_dbm`
   - `timestamp_utc`
   - `readings` (object; differs per device type)
   - `debug.sequence`
3. If auth is required, configure the app's **Authorization Header** (e.g., `Bearer <token>`).
4. Return a `2xx` response on successful ingestion.
5. Use dashboard rules/visuals for each device type:
   - door sensor: use `readings.door_closed`
   - thermometer: use `readings.temperature_c`
   - camera: use `readings.motion_detected` and optionally `readings.image_data_url`
   - switch: use `readings.switch_on` + `readings.level`

### Example payload

```json
{
  "timestamp_utc": "2026-03-13T12:00:00+00:00",
  "device_id": "door-001",
  "device_name": "Front Door Sensor",
  "device_type": "nb_iot_door_sensor",
  "serial_number": "SN-DOOR-1001",
  "battery_voltage": 3.7,
  "signal_strength_dbm": -75,
  "readings": {
    "door_closed": true,
    "tamper_detected": false,
    "network": "NB-IoT"
  },
  "debug": {
    "generated_at": "2026-03-13T12:00:00+00:00",
    "sequence": 12
  }
}
```

---

## Deployment (Render.com)

### Option A: Blueprint (recommended)

1. Push repo to GitHub/GitLab.
2. In Render, create a **Blueprint** and point to this repo.
3. Render reads `render.yaml` and creates the service automatically.
4. Set env vars in Render dashboard if you want overrides.

### Option B: Manual web service

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

---

## Debugging tips

- Server logs include event generation and forwarding status.
- Use `/api/health` to confirm backend is up.
- If forwarding fails, check:
  - endpoint URL correctness
  - TLS/cert validity
  - auth header value
  - response status in debug console

---

## Roadmap

### User-facing

- [x] Multi-device emulation UI
- [x] Door sensor, thermometer, camera, switch profiles
- [x] Webcam capture for camera simulation
- [x] Dashboard endpoint forwarding with auth header
- [ ] Scheduled auto-emission per device (interval runner)
- [ ] Payload templates + scenario presets (normal/day/night/alarm)
- [ ] CSV export of generated test telemetry

### Under-the-hood

- [x] Typed validation models and centralized simulation service
- [x] Basic test suite for simulator
- [ ] Persistent storage for device profiles
- [ ] Role-based authentication (admin/tester)
- [ ] Rate limiting and API key support
- [ ] OpenTelemetry traces + metrics endpoint

---

## Major feature log (in order added)

- **Branch `work`**: Initial full-stack IoT dashboard spoofer with multi-device simulation, webcam camera emulation, endpoint forwarding, test suite, scripts, and deployment blueprint.

---

## License

Choose a license before production use (e.g., MIT, Apache-2.0, or proprietary).
