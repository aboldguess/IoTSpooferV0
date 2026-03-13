"""FastAPI application entrypoint.

Purpose:
- Expose APIs and a lightweight UI for emulating IoT devices.
- Serve static frontend assets for local and cloud deployment.

Structure:
- App initialization and middleware.
- API routes for device management, event generation, and forwarding.
- Static file hosting for the browser client.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import CameraUploadRequest, DashboardTarget, DeviceCommand, DeviceProfile, DispatchReceipt, DispatchResult, EndpointCheckResult
from app.services.dispatcher import DispatcherService
from app.services.simulator import SimulatorService

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

simulator = SimulatorService()
dispatcher = DispatcherService()

app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse("frontend/index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/devices")
def list_devices() -> list[dict]:
    return [state.profile.model_dump() for state in simulator.list_devices()]


@app.post("/api/devices")
def upsert_device(profile: DeviceProfile) -> dict:
    state = simulator.upsert_device(profile)
    logger.info("device_upserted device_id=%s type=%s", profile.id, profile.device_type.value)
    return {"message": "Device stored", "device": state.profile.model_dump()}


@app.post("/api/devices/{device_id}/command")
def apply_command(device_id: str, command: DeviceCommand) -> dict:
    if device_id not in {d.profile.id for d in simulator.list_devices()}:
        raise HTTPException(status_code=404, detail="Device not found")
    state = simulator.update_command(device_id, command)
    return {
        "message": "Command applied",
        "state": {
            "switch_state": state.switch_state,
            "switch_level": state.switch_level,
        },
    }


@app.post("/api/devices/{device_id}/camera")
def camera_upload(device_id: str, request: CameraUploadRequest) -> dict:
    if device_id not in {d.profile.id for d in simulator.list_devices()}:
        raise HTTPException(status_code=404, detail="Device not found")

    data_size = len(request.data_url.encode("utf-8"))
    if data_size > settings.max_camera_image_bytes:
        raise HTTPException(status_code=413, detail="Image exceeds configured size limit")

    simulator.update_camera_frame(device_id, request.data_url)
    return {"message": "Camera snapshot updated"}


@app.post("/api/devices/{device_id}/emit", response_model=DispatchResult)
async def emit_event(device_id: str, target: DashboardTarget | None = None) -> DispatchResult:
    if device_id not in {d.profile.id for d in simulator.list_devices()}:
        raise HTTPException(status_code=404, detail="Device not found")

    payload = simulator.generate_event(device_id)
    logger.info("event_generated device_id=%s", device_id)

    if target is None:
        return DispatchResult(accepted=True, forwarded=False, message="Generated locally", payload=payload)

    return await dispatcher.forward(payload, target)


@app.post("/api/endpoint/check", response_model=EndpointCheckResult)
async def check_endpoint(target: DashboardTarget) -> EndpointCheckResult:
    """Actively probe an endpoint to confirm it is listening/reachable."""
    return await dispatcher.check_endpoint(target)


@app.get("/api/endpoint/receipts", response_model=list[DispatchReceipt])
def endpoint_receipts(
    endpoint_url: str | None = Query(default=None, max_length=2048),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[DispatchReceipt]:
    """Return recent forwarding receipts for delivery verification and debugging."""
    return dispatcher.list_receipts(endpoint_url=endpoint_url, limit=limit)
