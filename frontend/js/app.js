/**
 * app.js - Main Client Controller for OmiMind (v2.1)
 * Ambient Audio Canvas Waveform + 5-Agent Swarm Stream Controller
 */
import * as api from './api.js';
import * as ui from './ui.js';
import { setupVoiceCapture } from './audio.js';

let activeMeetingId = 'q4_strategy';
let voiceEngine = null;
let searchDebounceTimer = null;
let isAudioActive = false;

window.switchTab = ui.switchTab;
window.copyEmailText = ui.copyEmailText;
window.copyJiraText = ui.copyJiraText;
window.downloadICS = ui.downloadICS;

window.selectMeeting = function(id) {
  activeMeetingId = id;
  ui.updateMeetingButtons(id);
  ui.showToast(`Selected: ${id.replace('_', ' ').toUpperCase()}`);
};

async function runStreamingPipeline(endpoint, body) {
  ui.showPipelinePanel();
  const btn = document.getElementById('btn-process');
  if (btn) { btn.innerText = 'Running 5-Agent Swarm...'; btn.disabled = true; }
  isAudioActive = true;

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
            ui.showToast('5-Agent Swarm Orchestration Complete!');
          } else {
            ui.updatePipelineAgent(event);
          }
        } catch (_) {}
      }
    }
  } catch (e) {
    console.error('Streaming pipeline failed', e);
    ui.showToast('Processing error: ' + e.message, 'warning');
  } finally {
    if (btn) { btn.innerText = 'Ingest & Run Lyzr Swarm'; btn.disabled = false; }
    setTimeout(() => { isAudioActive = false; }, 1000);
  }
}

window.processActiveMeeting = async function() {
  await runStreamingPipeline('/api/process-stream', { meeting_id: activeMeetingId });
};

window.submitCustomVoice = async function() {
  const input = document.getElementById('live-voice-input');
  const text = input ? input.value.trim() : '';
  if (!text) return ui.showToast('Please speak or enter text first.', 'warning');
  await runStreamingPipeline('/api/custom-voice-stream', { transcript: text, speaker: 'Voice Input' });
};

window.searchMemory = async function() {
  const input = document.getElementById('query-input');
  const q = input ? input.value.trim() : '';
  if (!q) return;
  try {
    const res = await api.queryMemory(q);
    ui.renderQueryResult(res);
  } catch (e) {
    console.error('Search failed', e);
  }
};

window.toggleMic = async function() {
  const statusEl = document.getElementById('mic-status');
  const btnText = document.getElementById('mic-btn-text');
  const input = document.getElementById('live-voice-input');

  if (!voiceEngine) {
    voiceEngine = setupVoiceCapture({
      onTranscript: (t) => {
        if (input) input.value = t;
      },
      onStatus: (s) => {
        if (statusEl) statusEl.innerText = s;
        if (s.includes('Listening')) {
          if (btnText) btnText.innerText = 'Stop Mic';
          isAudioActive = true;
          ui.showToast('Omi Ambient Voice Stream active');
        } else {
          if (btnText) btnText.innerText = 'Record Voice';
          isAudioActive = false;
        }
      }
    });
  }

  voiceEngine.toggle();
};

// ─── Ambient Audio Waveform Canvas Animation Loop ─────────────────────────────

function initWaveformCanvas() {
  const canvas = document.getElementById('ambient-waveform');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let step = 0;

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const width = canvas.width;
    const height = canvas.height;
    const mid = height / 2;

    const baseAmp = isAudioActive ? 12 : 2.5;
    const speed = isAudioActive ? 0.08 : 0.02;
    step += speed;

    // Draw background subtle grid lines
    ctx.strokeStyle = 'rgba(30, 41, 59, 0.4)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, mid);
    ctx.lineTo(width, mid);
    ctx.stroke();

    // Primary cyan wave
    ctx.beginPath();
    ctx.strokeStyle = isAudioActive ? '#06b6d4' : '#38bdf888';
    ctx.lineWidth = isAudioActive ? 2 : 1.2;

    for (let x = 0; x < width; x++) {
      const y = mid + Math.sin(x * 0.04 + step) * baseAmp * Math.sin(x * 0.01 + step * 0.5);
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Secondary purple harmonics
    if (isAudioActive) {
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(168, 85, 247, 0.6)';
      ctx.lineWidth = 1.5;
      for (let x = 0; x < width; x++) {
        const y = mid + Math.cos(x * 0.05 - step) * (baseAmp * 0.7);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }

    requestAnimationFrame(draw);
  }

  requestAnimationFrame(draw);
}

// ─── Live Search Debounce ──────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  const queryInput = document.getElementById('query-input');
  if (queryInput) {
    queryInput.addEventListener('input', () => {
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(() => {
        window.searchMemory();
      }, 400);
    });
  }

  initWaveformCanvas();
});
