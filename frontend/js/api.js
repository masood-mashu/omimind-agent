/**
 * api.js - Centralized OmiMind 2.0 Backend Client
 * Connects to Qdrant vector memory, Lyzr agent synthesis, and SSE pipeline.
 * Transmits secure HttpOnly session cookies automatically with all requests.
 */

const API_BASE = '';

async function handleResponse(res, errorMessage = 'Request failed') {
  if (!res.ok) {
    if (res.status === 401 && typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('omimind:unauthorized'));
    }
    let errorDetail = `${errorMessage} (HTTP ${res.status})`;
    try {
      const data = await res.json();
      if (data?.error?.message) errorDetail = data.error.message;
      else if (data?.detail) errorDetail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    } catch (_) {}
    throw new Error(errorDetail);
  }
  return res.json();
}

export async function login(secretKey) {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ secret_key: secretKey }),
    credentials: 'same-origin',
  });
  return handleResponse(res, 'Authentication failed');
}

export async function logout() {
  const res = await fetch(`${API_BASE}/api/auth/logout`, {
    method: 'POST',
    credentials: 'same-origin',
  });
  return handleResponse(res, 'Logout failed');
}

export async function checkAuthStatus() {
  const res = await fetch(`${API_BASE}/api/auth/status`, {
    credentials: 'same-origin',
  });
  return handleResponse(res, 'Failed to check authentication status');
}

export async function fetchHealth() {
  return handleResponse(await fetch(`${API_BASE}/health`, { credentials: 'same-origin' }), 'Health check failed');
}

export async function fetchMeetings() {
  return handleResponse(await fetch(`${API_BASE}/api/meetings`, { credentials: 'same-origin' }), 'Failed to fetch meetings');
}

export async function fetchMeetingDetail(meetingId) {
  return handleResponse(
    await fetch(`${API_BASE}/api/meetings/${encodeURIComponent(meetingId)}`, { credentials: 'same-origin' }),
    'Failed to fetch meeting detail'
  );
}

export async function fetchMemories(limit = 30, uid = 'default_user') {
  const url = `${API_BASE}/api/memories?limit=${limit}&uid=${encodeURIComponent(uid)}`;
  return handleResponse(await fetch(url, { credentials: 'same-origin' }), 'Failed to fetch memories');
}

export async function fetchActions() {
  return handleResponse(await fetch(`${API_BASE}/api/actions`, { credentials: 'same-origin' }), 'Failed to fetch action items');
}

export async function askMemory(question, limit = 5, uid = 'default_user') {
  const res = await fetch(`${API_BASE}/api/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, limit, uid }),
    credentials: 'same-origin',
  });
  return handleResponse(res, 'Memory reasoning failed');
}

export async function queryMemory(question, limit = 4, uid = 'default_user') {
  const res = await fetch(`${API_BASE}/api/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, limit, uid }),
    credentials: 'same-origin',
  });
  return handleResponse(res, 'Semantic search failed');
}

export async function processMeeting(meetingId) {
  const res = await fetch(`${API_BASE}/api/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ meeting_id: meetingId }),
    credentials: 'same-origin',
  });
  return handleResponse(res, 'Failed to process meeting');
}

export async function forgetMemory(sessionId = null, pointId = null) {
  let url = `${API_BASE}/api/forget?`;
  if (sessionId) url += `session_id=${encodeURIComponent(sessionId)}&`;
  if (pointId) url += `point_id=${encodeURIComponent(pointId)}`;
  return handleResponse(await fetch(url, { method: 'POST', credentials: 'same-origin' }), 'Failed to delete memory');
}

export async function seedDemoData() {
  return handleResponse(await fetch(`${API_BASE}/api/seed`, { method: 'POST', credentials: 'same-origin' }), 'Failed to seed demo data');
}

/**
 * Shared SSE Reader for meeting and voice streams.
 */
export async function streamPipeline(endpoint, body, callbacks = {}) {
  const { onEvent, onError, onComplete } = callbacks;
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      credentials: 'same-origin',
    });
    if (!response.ok) throw new Error(`Stream request failed with HTTP ${response.status}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop();
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith('data: ')) continue;
        try {
          const event = JSON.parse(line.slice(6));
          if (event.type === 'complete') {
            if (onComplete) onComplete(event.dossier);
          } else if (event.type === 'error') {
            if (onError) onError(event);
          } else {
            if (onEvent) onEvent(event);
          }
        } catch (parseErr) {
          console.warn('Failed to parse SSE line:', line, parseErr);
        }
      }
    }
  } catch (err) {
    if (onError) onError({ message: err.message || 'Stream connection failed' });
    throw err;
  }
}
