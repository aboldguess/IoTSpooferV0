/*
File Guide: frontend/app.js
- Purpose: Browser-side logic for device management plus HTTP and MQTT integration tests.
- Structure: API helper functions, UI event handlers, and debug logging utilities.
*/

const output = document.getElementById("output");
const deviceForm = document.getElementById("device-form");
const deviceSelect = document.getElementById("device-select");
const emitBtn = document.getElementById("emit-event");
const checkEndpointBtn = document.getElementById("check-endpoint");
const viewReceiptsBtn = document.getElementById("view-receipts");
const sendVerifyBtn = document.getElementById("send-verify");
const sendCommandBtn = document.getElementById("send-command");
const startCameraBtn = document.getElementById("start-camera");
const captureFrameBtn = document.getElementById("capture-frame");
const cameraVideo = document.getElementById("camera-preview");

const mqttTestBtn = document.getElementById("mqtt-test-connection");
const mqttPublishBtn = document.getElementById("mqtt-publish");
const mqttSubscribeBtn = document.getElementById("mqtt-subscribe");
const mqttEnrollBtn = document.getElementById("mqtt-enroll");
const mqttEmitEnrolledBtn = document.getElementById("mqtt-emit-enrolled");
const mqttListEnrollmentsBtn = document.getElementById("mqtt-list-enrollments");

let stream = null;
let latestCameraFrame = null;

function readMqttConfig() {
  return {
    host: document.getElementById("mqtt-host").value.trim(),
    port: Number(document.getElementById("mqtt-port").value),
    client_id: document.getElementById("mqtt-client-id").value.trim(),
    username: document.getElementById("mqtt-username").value.trim() || null,
    password: document.getElementById("mqtt-password").value || null,
    keepalive_seconds: 30,
    tls_enabled: document.getElementById("mqtt-tls").checked,
  };
}

function readMqttTopicOptions() {
  return {
    topic: document.getElementById("mqtt-topic").value.trim(),
    qos: Number(document.getElementById("mqtt-qos").value),
  };
}

function readTargetConfig() {
  const endpoint = document.getElementById("endpoint-url").value.trim();
  const auth = document.getElementById("auth-header").value.trim();
  if (!endpoint) return null;
  return { endpoint_url: endpoint, auth_header_value: auth || null, timeout_seconds: 8 };
}

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
}

async function emitForSelectedDevice() {
  const id = deviceSelect.value;
  if (!id) return log("No device selected for emit action");
  const payload = readTargetConfig();
  const result = await api(`/api/devices/${encodeURIComponent(id)}/emit`, { method: "POST", body: JSON.stringify(payload) });
  return { id, payload, result };
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
    const result = await api(`/api/devices/${encodeURIComponent(id)}/command`, { method: "POST", body: JSON.stringify(payload) });
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
  canvas.getContext("2d").drawImage(cameraVideo, 0, 0, canvas.width, canvas.height);
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

checkEndpointBtn.addEventListener("click", async () => {
  const payload = readTargetConfig();
  if (!payload) return log("Provide endpoint URL before checking listener status");
  try {
    log("Endpoint listener check result", await api("/api/endpoint/check", { method: "POST", body: JSON.stringify(payload) }));
  } catch (error) {
    log(`Endpoint listener check failed: ${error.message}`);
  }
});

viewReceiptsBtn.addEventListener("click", async () => {
  const payload = readTargetConfig();
  const query = payload ? `?endpoint_url=${encodeURIComponent(payload.endpoint_url)}&limit=20` : "?limit=20";
  try {
    log("Recent endpoint delivery receipts", await api(`/api/endpoint/receipts${query}`));
  } catch (error) {
    log(`Unable to fetch delivery receipts: ${error.message}`);
  }
});

emitBtn.addEventListener("click", async () => {
  try {
    const emitted = await emitForSelectedDevice();
    if (emitted) log("Event generated", emitted.result);
  } catch (error) {
    log(`Error generating event: ${error.message}`);
  }
});

sendVerifyBtn.addEventListener("click", async () => {
  try {
    const emitted = await emitForSelectedDevice();
    if (!emitted?.payload?.endpoint_url) return log("Verification skipped: no endpoint configured");
    const receipts = await api(`/api/endpoint/receipts?endpoint_url=${encodeURIComponent(emitted.payload.endpoint_url)}&limit=1`);
    const latest = receipts[0];
    if (!latest) return log("Verification warning: no receipt found yet", receipts);
    log(latest.status_code >= 200 && latest.status_code < 300 ? "Verification PASSED" : "Verification FAILED", latest);
  } catch (error) {
    log(`Send + verify failed: ${error.message}`);
  }
});

mqttTestBtn.addEventListener("click", async () => {
  try {
    log("MQTT connection test", await api("/api/mqtt/connect", { method: "POST", body: JSON.stringify(readMqttConfig()) }));
  } catch (error) {
    log(`MQTT connection error: ${error.message}`);
  }
});

mqttPublishBtn.addEventListener("click", async () => {
  const { topic, qos } = readMqttTopicOptions();
  if (!topic) return log("Provide MQTT topic before publishing");
  try {
    const payloadInput = document.getElementById("mqtt-payload").value.trim();
    let payload = payloadInput;
    if (payloadInput.startsWith("{") || payloadInput.startsWith("[")) {
      payload = JSON.parse(payloadInput);
    }
    const result = await api("/api/mqtt/publish", {
      method: "POST",
      body: JSON.stringify({ config: readMqttConfig(), request: { topic, qos, retain: false, payload } }),
    });
    log("MQTT publish result", result);
  } catch (error) {
    log(`MQTT publish error: ${error.message}`);
  }
});

mqttSubscribeBtn.addEventListener("click", async () => {
  const { topic, qos } = readMqttTopicOptions();
  if (!topic) return log("Provide MQTT topic before subscribing");
  try {
    const result = await api("/api/mqtt/subscribe", {
      method: "POST",
      body: JSON.stringify({ config: readMqttConfig(), request: { topic, qos, wait_seconds: 8 } }),
    });
    log("MQTT subscribe-once result", result);
  } catch (error) {
    log(`MQTT subscribe error: ${error.message}`);
  }
});

mqttEnrollBtn.addEventListener("click", async () => {
  const id = deviceSelect.value;
  const { topic, qos } = readMqttTopicOptions();
  if (!id) return log("Select a device before enrollment");
  if (!topic) return log("Provide MQTT topic before enrollment");
  try {
    log("Sensor enrolled to MQTT topic", await api("/api/mqtt/enroll", {
      method: "POST",
      body: JSON.stringify({ device_id: id, topic, qos, retain: false }),
    }));
  } catch (error) {
    log(`MQTT enrollment error: ${error.message}`);
  }
});

mqttEmitEnrolledBtn.addEventListener("click", async () => {
  const id = deviceSelect.value;
  if (!id) return log("Select a device before MQTT telemetry emission");
  try {
    log("MQTT telemetry emit result", await api(`/api/devices/${encodeURIComponent(id)}/emit/mqtt`, {
      method: "POST",
      body: JSON.stringify({ broker: readMqttConfig() }),
    }));
  } catch (error) {
    log(`MQTT telemetry emit error: ${error.message}`);
  }
});

mqttListEnrollmentsBtn.addEventListener("click", async () => {
  try {
    log("Current MQTT enrollments", await api("/api/mqtt/enrollments"));
  } catch (error) {
    log(`Unable to list enrollments: ${error.message}`);
  }
});

refreshDevices().then(() => log("Device list loaded")).catch((error) => log(`Device refresh failed: ${error.message}`));
