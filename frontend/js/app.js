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
window.openGmailCompose = ui.openGmailCompose;
window.openMailto = ui.openMailto;
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
  const btn = document.getElementById('btn-mic');
  const input = document.getElementById('live-voice-input');

  if (!voiceEngine) {
    voiceEngine = setupVoiceCapture({
      onTranscript: (t) => {
        if (input) {
          input.value = t;
          input.scrollTop = input.scrollHeight;
        }
      },
      onStatus: (s) => {
        if (statusEl) statusEl.innerText = s;
        if (s.includes('Listening')) {
          if (btnText) btnText.innerText = 'Stop Mic';
          if (btn) {
            btn.className = "flex-1 py-2 px-3 rounded-xl border border-rose-500/60 bg-rose-500/20 hover:bg-rose-500/30 text-xs font-medium transition flex items-center justify-center gap-2 text-rose-300 shadow-lg shadow-rose-500/20 animate-pulse";
          }
          isAudioActive = true;
          ui.showToast('Microphone active: Streaming ambient voice...');
        } else {
          if (btnText) btnText.innerText = 'Record Voice';
          if (btn) {
            btn.className = "flex-1 py-2 px-3 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-xs font-medium transition flex items-center justify-center gap-2 text-cyan-300";
          }
          isAudioActive = false;
        }
      },
      onError: (err) => {
        ui.showToast(err.message || 'Microphone error', 'warning');
      }
    });
  }

  await voiceEngine.toggle();
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

    let baseAmp = isAudioActive ? 12 : 2.5;

    // React in real-time to microphone volume frequencies if available
    if (voiceEngine && voiceEngine.getAudioFrequencyData) {
      const freq = voiceEngine.getAudioFrequencyData();
      if (freq && freq.length > 0) {
        let sum = 0;
        for (let i = 0; i < freq.length; i++) sum += freq[i];
        const avg = sum / freq.length;
        if (avg > 2) {
          baseAmp = Math.max(baseAmp, avg * 0.35);
        }
      }
    }

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
