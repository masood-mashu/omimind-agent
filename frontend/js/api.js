/**
 * api.js - Centralized OMIMIND 2.0 Backend Client
 * Connects to Qdrant vector memory, Lyzr agent synthesis, and SSE pipeline.
 * Attaches the current Supabase access token to protected API requests.
 */

import { getAccessToken, signIn, signOut } from './supabase.js';

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

async function authHeaders(extra = {}) {
  const token = await getAccessToken();
  return { ...extra, ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}

export { signIn as login, signOut as logout };

export async function authorizedFetch(url, options = {}) {
  const headers = await authHeaders(options.headers || {});
  return fetch(url, { ...options, headers, credentials: 'same-origin' });
}

export async function checkAuthStatus() {
  const res = await authorizedFetch(`${API_BASE}/api/auth/status`);
  return handleResponse(res, 'Failed to check authentication status');
}

export async function fetchHealth() {
  return handleResponse(await authorizedFetch(`${API_BASE}/health`), 'Health check failed');
}

export async function fetchMeetings() {
  return handleResponse(await authorizedFetch(`${API_BASE}/api/meetings`), 'Failed to fetch meetings');
}

export async function fetchMeetingDetail(meetingId) {
  return handleResponse(
    await authorizedFetch(`${API_BASE}/api/meetings/${encodeURIComponent(meetingId)}`),
    'Failed to fetch meeting detail'
  );
}

export async function fetchMemories(limit = 30) {
  const url = `${API_BASE}/api/memories?limit=${limit}`;
  return handleResponse(await authorizedFetch(url), 'Failed to fetch memories');
}

export async function fetchActions() {
  return handleResponse(await authorizedFetch(`${API_BASE}/api/actions`), 'Failed to fetch action items');
}

export async function askMemory(question, limit = 5) {
  const res = await fetch(`${API_BASE}/api/ask`, {
    method: 'POST',
    headers: await authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ question, limit }),
  });
  return handleResponse(res, 'Memory reasoning failed');
}

export async function queryMemory(question, limit = 4) {
  const res = await fetch(`${API_BASE}/api/query`, {
    method: 'POST',
    headers: await authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ question, limit }),
  });
  return handleResponse(res, 'Semantic search failed');
}

export async function processMeeting(meetingId) {
  const res = await fetch(`${API_BASE}/api/process`, {
    method: 'POST',
    headers: await authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ meeting_id: meetingId }),
  });
  return handleResponse(res, 'Failed to process meeting');
}

export async function forgetMemory(sessionId = null, pointId = null) {
  let url = `${API_BASE}/api/forget?`;
  if (sessionId) url += `session_id=${encodeURIComponent(sessionId)}&`;
  if (pointId) url += `point_id=${encodeURIComponent(pointId)}`;
  return handleResponse(await authorizedFetch(url, { method: 'POST' }), 'Failed to delete memory');
}

export async function seedDemoData() {
  return handleResponse(await authorizedFetch(`${API_BASE}/api/seed`, { method: 'POST' }), 'Failed to seed demo data');
}

/**
 * Shared SSE Reader for meeting and voice streams.
 */
export async function streamPipeline(endpoint, body, callbacks = {}) {
  const { onEvent, onError, onComplete } = callbacks;
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: await authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
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
          if (event.type === 'complete' || event.type === 'pipeline_completed') {
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
