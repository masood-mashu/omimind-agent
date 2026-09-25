/**
 * app.js - Main Client Controller for OmiMind
 */
import * as api from './api.js';
import * as ui from './ui.js';
import { setupVoiceCapture } from './audio.js';

let activeMeetingId = 'q4_strategy';
let voiceEngine = null;

// Expose switchTab globally for inline button onclick handlers
window.switchTab = ui.switchTab;

window.selectMeeting = function(id) {
  activeMeetingId = id;
  ui.updateMeetingButtons(id);
};

window.processActiveMeeting = async function() {
  const btn = document.getElementById('btn-process');
  if (btn) {
    btn.innerText = "Ingesting into Qdrant...";
    btn.disabled = true;
  }

  try {
    const data = await api.processMeeting(activeMeetingId);
    ui.renderDossier(data);
  } catch (e) {
    console.error("Processing failed", e);
    alert("Processing failed: " + e.message);
  } finally {
    if (btn) {
      btn.innerText = "Ingest & Run Lyzr Swarm";
      btn.disabled = false;
    }
  }
};

window.submitCustomVoice = async function() {
  const input = document.getElementById('live-voice-input');
  const text = input ? input.value.trim() : '';
  if (!text) return alert("Please speak or enter text first.");

  try {
    const data = await api.submitCustomVoice(text, "Masood (Builder)");
    ui.renderDossier(data);
  } catch (e) {
    console.error("Custom voice submission failed", e);
    alert("Voice submission failed: " + e.message);
  }
};

window.searchMemory = async function() {
  const input = document.getElementById('query-input');
  const q = input ? input.value.trim() : '';
  if (!q) return;

  try {
    const data = await api.queryMemory(q);
    ui.renderQueryResult(data);
  } catch (e) {
    console.error("Search failed", e);
  }
};

window.copyEmailText = function() {
  const bodyEl = document.getElementById('email-body');
  if (bodyEl) {
    navigator.clipboard.writeText(bodyEl.innerText);
    alert("Follow-up email copied to clipboard!");
  }
};

// Initialize voice capture
document.addEventListener('DOMContentLoaded', async () => {
  const micStatus = document.getElementById('mic-status');
  const micBtnText = document.getElementById('mic-btn-text');
  const liveVoiceInput = document.getElementById('live-voice-input');

  voiceEngine = setupVoiceCapture({
    onStart: () => {
      if (micStatus) {
        micStatus.innerText = "🔴 Listening via Omi Stream...";
        micStatus.className = "text-xs text-rose-400 font-mono animate-pulse";
      }
      if (micBtnText) micBtnText.innerText = "Stop Recording";
    },
    onResult: (transcript) => {
      if (liveVoiceInput) liveVoiceInput.value = transcript;
    },
    onEnd: () => {
      if (micStatus) {
        micStatus.innerText = "Idle";
        micStatus.className = "text-xs text-slate-500 font-mono";
      }
      if (micBtnText) micBtnText.innerText = "Record Voice";
    },
    onError: () => {
      if (micStatus) {
        micStatus.innerText = "Idle";
        micStatus.className = "text-xs text-slate-500 font-mono";
      }
      if (micBtnText) micBtnText.innerText = "Record Voice";
    }
  });

  window.toggleMic = () => {
    if (voiceEngine) voiceEngine.toggle();
  };

  // Fetch health stats to check Qdrant connection
  try {
    const health = await api.fetchHealth();
    const badge = document.getElementById('qdrant-points-badge');
    if (badge && health.qdrant_stats) {
      badge.innerText = `${health.qdrant_stats.points_count} Points`;
    }
  } catch (e) {
    console.warn("Health check offline", e);
  }
});
