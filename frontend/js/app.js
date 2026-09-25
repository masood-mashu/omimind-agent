/**
 * app.js - Main Client Controller for OmiMind (v2 - SSE Streaming)
 */
import * as api from './api.js';
import * as ui from './ui.js';
import { setupVoiceCapture } from './audio.js';

let activeMeetingId = 'q4_strategy';
let voiceEngine = null;
let searchDebounceTimer = null;

window.switchTab = ui.switchTab;

window.selectMeeting = function(id) {
  activeMeetingId = id;
  ui.updateMeetingButtons(id);
};

async function runStreamingPipeline(endpoint, body) {
  ui.showPipelinePanel();
  const btn = document.getElementById('btn-process');
  if (btn) { btn.innerText = 'Running Lyzr Swarm...'; btn.disabled = true; }

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

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
            ui.renderDossier(event.dossier);
            const badge = document.getElementById('qdrant-points-badge');
            if (badge) badge.innerText = `${event.dossier.indexed_vectors_count} Vectors`;
          } else {
            ui.updatePipelineAgent(event);
          }
        } catch (_) {}
      }
    }
  } catch (e) {
    console.error('Streaming pipeline failed', e);
    alert('Processing failed: ' + e.message);
  } finally {
    if (btn) { btn.innerText = 'Ingest & Run Lyzr Swarm'; btn.disabled = false; }
  }
}

window.processActiveMeeting = async function() {
  await runStreamingPipeline('/api/process-stream', { meeting_id: activeMeetingId });
};

window.submitCustomVoice = async function() {
  const input = document.getElementById('live-voice-input');
  const text = input ? input.value.trim() : '';
  if (!text) return alert('Please speak or enter text first.');
  await runStreamingPipeline('/api/custom-voice-stream', { transcript: text, speaker: 'Voice Input' });
};

window.searchMemory = async function() {
  const input = document.getElementById('query-input');
  const q = input ? input.value.trim() : '';
  if (!q) return;
  try {
    const data = await api.queryMemory(q);
    ui.renderQueryResult(data);
  } catch (e) { console.error('Search failed', e); }
};

function setupLiveSearch() {
  const input = document.getElementById('query-input');
  if (!input) return;
  input.addEventListener('input', () => {
    clearTimeout(searchDebounceTimer);
    const q = input.value.trim();
    if (q.length < 4) return;
    searchDebounceTimer = setTimeout(() => window.searchMemory(), 400);
  });
}

window.copyEmailText = function() {
  const bodyEl = document.getElementById('email-body');
  if (bodyEl) {
    navigator.clipboard.writeText(bodyEl.innerText);
    alert('Follow-up email copied to clipboard!');
  }
};

document.addEventListener('DOMContentLoaded', async () => {
  const micStatus = document.getElementById('mic-status');
  const micBtnText = document.getElementById('mic-btn-text');
  const liveVoiceInput = document.getElementById('live-voice-input');

  voiceEngine = setupVoiceCapture({
    onStart: () => {
      if (micStatus) { micStatus.innerText = 'Listening via Omi Stream...'; micStatus.className = 'text-xs text-rose-400 font-mono animate-pulse'; }
      if (micBtnText) micBtnText.innerText = 'Stop Recording';
    },
    onResult: (transcript) => { if (liveVoiceInput) liveVoiceInput.value = transcript; },
    onEnd: () => {
      if (micStatus) { micStatus.innerText = 'Idle'; micStatus.className = 'text-xs text-slate-500 font-mono'; }
      if (micBtnText) micBtnText.innerText = 'Record Voice';
    },
    onError: () => {
      if (micStatus) { micStatus.innerText = 'Idle'; micStatus.className = 'text-xs text-slate-500 font-mono'; }
      if (micBtnText) micBtnText.innerText = 'Record Voice';
    }
  });

  window.toggleMic = () => { if (voiceEngine) voiceEngine.toggle(); };
  setupLiveSearch();

  try {
    const health = await api.fetchHealth();
    const badge = document.getElementById('qdrant-points-badge');
    if (badge && health.qdrant_stats) {
      badge.innerText = health.qdrant_stats.points_count > 0
        ? `${health.qdrant_stats.points_count} Vectors` : 'Active';
    }
  } catch (e) { console.warn('Health check offline', e); }
});
