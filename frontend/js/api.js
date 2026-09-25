/**
 * api.js - OmiMind Backend API Client
 */
const API_BASE = '';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchMeetings() {
  const res = await fetch(`${API_BASE}/api/meetings`);
  if (!res.ok) throw new Error('Failed to fetch meetings');
  return res.json();
}

export async function processMeeting(meetingId) {
  const res = await fetch(`${API_BASE}/api/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ meeting_id: meetingId })
  });
  if (!res.ok) throw new Error('Failed to process meeting');
  return res.json();
}

export async function submitCustomVoice(transcript, speaker = 'Masood (Builder)') {
  const res = await fetch(`${API_BASE}/api/custom-voice`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transcript, speaker })
  });
  if (!res.ok) throw new Error('Failed to ingest custom voice memo');
  return res.json();
}

export async function queryMemory(question, limit = 4) {
  const res = await fetch(`${API_BASE}/api/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, limit })
  });
  if (!res.ok) throw new Error('Semantic search failed');
  return res.json();
}
