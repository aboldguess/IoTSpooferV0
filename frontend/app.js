/*
File Guide: frontend/app.js
- Purpose: Browser-side logic for managing virtual devices, webcam capture, and telemetry emission.
- Structure: API helper functions, UI event handlers, and debug logging utilities.
*/

const output = document.getElementById("output");
const deviceForm = document.getElementById("device-form");
const deviceSelect = document.getElementById("device-select");
const emitBtn = document.getElementById("emit-event");
const sendCommandBtn = document.getElementById("send-command");
const startCameraBtn = document.getElementById("start-camera");
const captureFrameBtn = document.getElementById("capture-frame");
const cameraVideo = document.getElementById("camera-preview");

let stream = null;
let latestCameraFrame = null;

const log = (message, data = null) => {
  const stamp = new Date().toISOString();
  const serialized = data ? `\n${JSON.stringify(data, null, 2)}` : "";
  output.textContent = `[${stamp}] ${message}${serialized}\n\n` + output.textContent;
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || payload.message || "Request failed");
  return payload;
}

async function refreshDevices() {
  const devices = await api("/api/devices");
  deviceSelect.innerHTML = "";
  devices.forEach((device) => {
    const option = document.createElement("option");
    option.value = device.id;
    option.textContent = `${device.device_name} (${device.device_type})`;
    deviceSelect.appendChild(option);
  });
  log("Device list refreshed", devices);
}

deviceForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(deviceForm));
  data.battery_voltage = Number(data.battery_voltage);
  data.signal_strength_dbm = Number(data.signal_strength_dbm);
  try {
    const result = await api("/api/devices", { method: "POST", body: JSON.stringify(data) });
    log("Device saved", result);
    await refreshDevices();
  } catch (error) {
    log(`Error saving device: ${error.message}`);
  }
});

sendCommandBtn.addEventListener("click", async () => {
  const id = deviceSelect.value;
  if (!id) return log("No device selected for command");

  const payload = {
    switch_state: document.getElementById("switch-state").checked,
    switch_level: Number(document.getElementById("switch-level").value),
  };

  try {
    const result = await api(`/api/devices/${encodeURIComponent(id)}/command`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    log("Switch command applied", result);
  } catch (error) {
    log(`Error applying command: ${error.message}`);
  }
});

startCameraBtn.addEventListener("click", async () => {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true });
    cameraVideo.srcObject = stream;
    log("Webcam started");
  } catch (error) {
    log(`Unable to start camera: ${error.message}`);
  }
});

captureFrameBtn.addEventListener("click", async () => {
  const id = deviceSelect.value;
  if (!id) return log("No device selected for camera upload");
  if (!stream) return log("Start webcam first");

  const canvas = document.createElement("canvas");
  canvas.width = cameraVideo.videoWidth || 640;
  canvas.height = cameraVideo.videoHeight || 480;
  const context = canvas.getContext("2d");
  context.drawImage(cameraVideo, 0, 0, canvas.width, canvas.height);
  latestCameraFrame = canvas.toDataURL("image/jpeg", 0.75);

  try {
    const result = await api(`/api/devices/${encodeURIComponent(id)}/camera`, {
      method: "POST",
      body: JSON.stringify({ data_url: latestCameraFrame }),
    });
    log("Camera frame uploaded", result);
  } catch (error) {
    log(`Error uploading frame: ${error.message}`);
  }
});

emitBtn.addEventListener("click", async () => {
  const id = deviceSelect.value;
  if (!id) return log("No device selected for emit action");

  const endpoint = document.getElementById("endpoint-url").value.trim();
  const auth = document.getElementById("auth-header").value.trim();
  const payload = endpoint
    ? {
        endpoint_url: endpoint,
        auth_header_value: auth || null,
        timeout_seconds: 8,
      }
    : null;

  try {
    const result = await api(`/api/devices/${encodeURIComponent(id)}/emit`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    log("Event generated", result);
  } catch (error) {
    log(`Error generating event: ${error.message}`);
  }
});

refreshDevices().catch((error) => log(`Device refresh failed: ${error.message}`));
