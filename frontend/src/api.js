import { auth } from './config/firebase';

export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const WS_BASE = API_BASE.replace(/^http/, 'ws');

export async function getAuthHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  try {
    await auth.authStateReady();
    const user = auth.currentUser;
    if (user) {
      const token = await user.getIdToken();
      headers['Authorization'] = `Bearer ${token}`;
    }
  } catch (err) {
    console.warn('[API] Failed to get auth token:', err);
  }
  return headers;
}

export async function fetchJSON(endpoint, options = {}) {
  const authHeaders = await getAuthHeaders();

  // Don't override Content-Type for FormData (browser sets multipart boundary)
  if (options.body instanceof FormData) {
    delete authHeaders['Content-Type'];
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      ...authHeaders,
      ...options.headers,
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }

  return res.json();
}

export const api = {
  // --- Dashboard & Stats ---
  getStats: (days = 30) => fetchJSON(`/api/stats?days=${days}`),

  getViolations: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return fetchJSON(`/api/violations?${q}`);
  },

  getOffenders: (limit = 20, days = 30) =>
    fetchJSON(`/api/offenders?limit=${limit}&days=${days}`),

  getZones: () => fetchJSON('/api/zones'),

  getVehicle: (plate, days = 90) =>
    fetchJSON(`/api/vehicle/${encodeURIComponent(plate)}?days=${days}`),

  getAnalytics: (days = 30) => fetchJSON(`/api/analytics?days=${days}`),

  // --- Processing ---
  processImage: async (file) => {
    const form = new FormData();
    form.append('file', file);
    return fetchJSON('/api/process-image', { method: 'POST', body: form });
  },

  processVideo: async (file) => {
    const form = new FormData();
    form.append('file', file);
    return fetchJSON('/api/process-video', { method: 'POST', body: form });
  },

  getProcessStatus: () => fetchJSON('/api/process-status'),

  // --- Demo & Seed ---
  seedDemo: () => fetchJSON('/api/seed-demo', { method: 'POST' }),

  // --- Feedback & Active Learning ---
  submitFeedback: async (data) => {
    const { file, plate, correctPlate, correctVehicleType, notes } = data;
    const form = new FormData();
    if (file) form.append('file', file);
    form.append('feedback', JSON.stringify({
      original_plate: plate || '',
      correct_plate: correctPlate || '',
      correct_vehicle_type: correctVehicleType || '',
      notes: notes || '',
    }));
    return fetchJSON('/api/feedback', { method: 'POST', body: form });
  },

  getFeedbackStats: () => fetchJSON('/api/feedback/stats'),

  submitFullImageFeedback: async (data) => {
    const { file, accuracyRating, missedVehicles, falseDetections, notes, totalDetected } = data;
    const form = new FormData();
    if (file) form.append('file', file);
    form.append('feedback', JSON.stringify({
      accuracy_rating: accuracyRating || 0,
      missed_vehicles: missedVehicles || 0,
      false_detections: falseDetections || 0,
      notes: notes || '',
      total_detected: totalDetected || 0,
    }));
    return fetchJSON('/api/feedback/full-image', { method: 'POST', body: form });
  },

  triggerRetrain: () => fetchJSON('/api/retrain', { method: 'POST' }),

  getModelInfo: () => fetchJSON('/api/model-info'),

  listModels: () => fetchJSON('/api/models/list'),

  setActiveModel: (category, modelName) => fetchJSON('/api/models/set-active', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category, model_name: modelName }),
  }),

  // --- Reports & Exports ---
  generateReport: async (plate, days = 30) => {
    const headers = await getAuthHeaders();
    const url = `${API_BASE}/api/generate-report?plate=${encodeURIComponent(plate)}&days=${days}`;
    const res = await fetch(url, { headers });
    if (!res.ok) {
      const err = await res.text().then(t => { try { return JSON.parse(t); } catch { return { error: t || 'Report generation failed' }; } });
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = `SVIES_Report_${plate}.pdf`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
    return { status: 'ok', message: 'Report downloaded' };
  },

  exportViolations: async (params = {}, format = 'csv') => {
    const headers = await getAuthHeaders();
    const q = new URLSearchParams({ ...params, format }).toString();
    const res = await fetch(`${API_BASE}/api/violations/export?${q}`, { headers });
    if (!res.ok) throw new Error(`Export failed: HTTP ${res.status}`);
    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = `svies_violations.${format}`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
    return { status: 'ok' };
  },

  exportOffenders: async (params = {}, format = 'csv') => {
    const headers = await getAuthHeaders();
    const q = new URLSearchParams({ ...params, format }).toString();
    const res = await fetch(`${API_BASE}/api/offenders/export?${q}`, { headers });
    if (!res.ok) throw new Error(`Export failed: HTTP ${res.status}`);
    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = `svies_offenders.${format}`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
    return { status: 'ok' };
  },

  // --- Webcam ---
  startWebcam: () => fetchJSON('/api/webcam/start', { method: 'POST' }),
  stopWebcam: () => fetchJSON('/api/webcam/stop', { method: 'POST' }),

  // --- Health ---
  health: () => fetchJSON('/api/health'),

  // --- Auth endpoints ---
  verifyAuth: () => fetchJSON('/api/auth/verify'),

  setUserRole: (uid, role) =>
    fetchJSON('/api/auth/set-role', {
      method: 'POST',
      body: JSON.stringify({ uid, role }),
    }),

  getUsers: () => fetchJSON('/api/auth/users'),

  createUser: (email, password, role, displayName = '') =>
    fetchJSON('/api/auth/create-user', {
      method: 'POST',
      body: JSON.stringify({ email, password, role, display_name: displayName }),
    }),

  deleteUser: (uid) =>
    fetchJSON('/api/auth/delete-user', {
      method: 'DELETE',
      body: JSON.stringify({ uid }),
    }),

  bootstrapAdmin: () =>
    fetchJSON('/api/auth/bootstrap-admin', { method: 'POST' }),

  // ── Vehicle Management ──
  getVehicles: (page = 1, search = '', perPage = 25) =>
    fetchJSON(`/api/vehicles?page=${page}&per_page=${perPage}&search=${encodeURIComponent(search)}`),

  addVehicle: (data) =>
    fetchJSON('/api/vehicles', { method: 'POST', body: JSON.stringify(data) }),

  updateVehicle: (plate, data) =>
    fetchJSON(`/api/vehicles/${encodeURIComponent(plate)}`, { method: 'PUT', body: JSON.stringify(data) }),

  deleteVehicle: (plate) =>
    fetchJSON(`/api/vehicles/${encodeURIComponent(plate)}`, { method: 'DELETE' }),

  updatePUCC: (plate, data) =>
    fetchJSON(`/api/vehicles/${encodeURIComponent(plate)}/pucc`, { method: 'PUT', body: JSON.stringify(data) }),

  updateInsurance: (plate, data) =>
    fetchJSON(`/api/vehicles/${encodeURIComponent(plate)}/insurance`, { method: 'PUT', body: JSON.stringify(data) }),

  setStolen: (plate, stolen) =>
    fetchJSON(`/api/vehicles/${encodeURIComponent(plate)}/stolen`, { method: 'PUT', body: JSON.stringify({ stolen }) }),
};

// --- WebSocket: Detection events ---
export function connectWebSocket(onMessage) {
  let ws = null;
  let cleanup = null;
  let reconnectTimeout = null;
  let closed = false;

  async function connect() {
    if (closed) return;

    // Clean up previous connection's ping interval before reconnecting
    if (cleanup) {
      cleanup();
      cleanup = null;
    }

    let tokenParam = '';
    try {
      const user = auth.currentUser;
      if (user) {
        const token = await user.getIdToken();
        tokenParam = `?token=${encodeURIComponent(token)}`;
      }
    } catch (err) {
      console.warn('[WS] Failed to get auth token:', err);
    }

    ws = new WebSocket(`${WS_BASE}/ws/live${tokenParam}`);

    ws.onopen = () => console.log('[WS] Connected');

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        onMessage(data);
      } catch (err) {
        console.error('[WS] Parse error:', err);
      }
    };

    ws.onclose = () => {
      console.log('[WS] Disconnected, reconnecting in 3s...');
      if (!closed) {
        reconnectTimeout = setTimeout(connect, 3000);
      }
    };

    ws.onerror = () => ws.close();

    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping');
    }, 30000);

    cleanup = () => {
      clearInterval(pingInterval);
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      ws.close();
    };
  }

  connect();

  return () => {
    closed = true;
    if (cleanup) cleanup();
  };
}

// --- WebSocket: Live camera feed ---
export function connectLiveFeed(onFrame) {
  let ws = null;
  let cleanup = null;
  let reconnectTimeout = null;
  let closed = false;

  async function connect() {
    if (closed) return;

    let tokenParam = '';
    try {
      const user = auth.currentUser;
      if (user) {
        const token = await user.getIdToken();
        tokenParam = `?token=${encodeURIComponent(token)}`;
      }
    } catch (err) {
      console.warn('[WS] Failed to get auth token:', err);
    }

    ws = new WebSocket(`${WS_BASE}/ws/live-feed${tokenParam}`);

    ws.onopen = () => console.log('[WS] Live feed connected');

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        onFrame(data);
      } catch (err) {
        console.error('[WS] Live feed parse error:', err);
      }
    };

    ws.onclose = () => {
      console.log('[WS] Live feed disconnected, reconnecting in 3s...');
      if (!closed) {
        reconnectTimeout = setTimeout(connect, 3000);
      }
    };

    ws.onerror = () => ws.close();

    cleanup = () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      ws.close();
    };
  }

  connect();

  return () => {
    closed = true;
    if (cleanup) cleanup();
  };
}
