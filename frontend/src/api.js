import { auth } from './config/firebase';

export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const WS_BASE = API_BASE.replace(/^http/, 'ws');

/* ── Auth helpers ── */

export async function getAuthHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  try {
    await auth.authStateReady();
    const user = auth.currentUser;
    if (user) {
      const token = await user.getIdToken(); // uses cache, fast
      headers['Authorization'] = `Bearer ${token}`;
    }
  } catch (_) { /* user may not be logged in */ }
  return headers;
}

/** Get a FRESH token (force refresh) — used only on 401 retry */
async function getFreshToken() {
  try {
    const user = auth.currentUser;
    if (user) return await user.getIdToken(true);
  } catch (_) { /* ignore */ }
  return null;
}

/* ── Core fetch with auto-retry on 401 ── */

export async function fetchJSON(endpoint, options = {}, _retried = false) {
  const authHeaders = await getAuthHeaders();

  if (options.body instanceof FormData) {
    delete authHeaders['Content-Type'];
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: { ...authHeaders, ...options.headers },
  });

  // Auto-retry ONCE on 401 with a fresh token
  if (res.status === 401 && !_retried) {
    const freshToken = await getFreshToken();
    if (freshToken) {
      const retryHeaders = { ...authHeaders, ...options.headers, Authorization: `Bearer ${freshToken}` };
      if (options.body instanceof FormData) delete retryHeaders['Content-Type'];
      const retryRes = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: retryHeaders,
      });
      if (retryRes.ok) return retryRes.json();
    }
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }

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

  refreshZones: (lat, lon, radiusM = 3000) =>
    fetchJSON(`/api/zones/refresh?lat=${lat}&lon=${lon}&radius_m=${radiusM}`, { method: 'POST' }),

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

/* ══════════════════════════════════════════════════════════
   WebSocket: Detection events (silent reconnect)
   ══════════════════════════════════════════════════════════ */
export function connectWebSocket(onMessage) {
  let ws = null;
  let cleanup = null;
  let reconnectTimeout = null;
  let closed = false;
  let retryDelay = 3000;

  async function connect() {
    if (closed) return;
    if (cleanup) { cleanup(); cleanup = null; }

    let tokenParam = '';
    try {
      await auth.authStateReady();
      const user = auth.currentUser;
      if (user) {
        const token = await user.getIdToken();
        tokenParam = `?token=${encodeURIComponent(token)}`;
      }
    } catch (_) { /* ignore */ }

    ws = new WebSocket(`${WS_BASE}/ws/live${tokenParam}`);

    ws.onopen = () => { retryDelay = 3000; };

    ws.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)); } catch (_) { /* ignore */ }
    };

    ws.onclose = () => {
      if (!closed) {
        retryDelay = Math.min(retryDelay * 1.5, 30000);
        reconnectTimeout = setTimeout(connect, retryDelay);
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
  return () => { closed = true; if (cleanup) cleanup(); };
}

/* ══════════════════════════════════════════════════════════
   WebSocket: Live camera feed (silent reconnect)
   ══════════════════════════════════════════════════════════ */
export function connectLiveFeed(onFrame) {
  let ws = null;
  let cleanup = null;
  let reconnectTimeout = null;
  let closed = false;
  let retryDelay = 3000;

  async function connect() {
    if (closed) return;
    if (cleanup) { cleanup(); cleanup = null; }

    let tokenParam = '';
    try {
      await auth.authStateReady();
      const user = auth.currentUser;
      if (user) {
        const token = await user.getIdToken();
        tokenParam = `?token=${encodeURIComponent(token)}`;
      }
    } catch (_) { /* ignore */ }

    ws = new WebSocket(`${WS_BASE}/ws/live-feed${tokenParam}`);

    ws.onopen = () => { retryDelay = 3000; };

    ws.onmessage = (e) => {
      try { onFrame(JSON.parse(e.data)); } catch (_) { /* ignore */ }
    };

    ws.onclose = () => {
      if (!closed) {
        retryDelay = Math.min(retryDelay * 1.5, 30000);
        reconnectTimeout = setTimeout(connect, retryDelay);
      }
    };

    ws.onerror = () => ws.close();

    cleanup = () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      ws.close();
    };
  }

  connect();
  return () => { closed = true; if (cleanup) cleanup(); };
}
