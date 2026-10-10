/**
 * app.js - Main Application Bootstrapper for OmiMind 2.0
 * Initializes state, navigation, audio engine, ambient waveform, and routing.
 */

import * as api from './api.js';
import { getState, setState, addPipelineEvent } from './state.js';
import { initNav } from './components/nav.js';
import { initRouter, navigate } from './router.js';
import { initWaveform } from './components/waveform.js';
import { setupVoiceCapture } from './audio.js';
import { showToast } from './components/toast.js';
import { openModal, closeModal } from './components/modal.js';

let voiceEngine = null;
let stopWaveform = null;

export async function refreshAppData() {
  try {
    const [health, meetingsData, memoriesData, actionsData] = await Promise.allSettled([
      api.fetchHealth(),
      api.fetchMeetings(),
      api.fetchMemories(30),
      api.fetchActions(),
    ]);

    const updates = {};
    if (health.status === 'fulfilled') updates.health = health.value;
    if (meetingsData.status === 'fulfilled') updates.meetings = meetingsData.value.meetings || [];
    if (memoriesData.status === 'fulfilled') updates.memories = memoriesData.value.memories || [];
    if (actionsData.status === 'fulfilled') updates.actions = actionsData.value.actions || [];

    setState(updates);
  } catch (err) {
    console.warn('Data refresh error:', err);
  }
}

function updateAuthButtonState(authenticated) {
  const label = document.getElementById('btn-auth-label');
  const btn = document.getElementById('btn-auth-toggle');
  if (label && btn) {
    if (authenticated) {
      label.innerText = 'Sign Out';
      btn.classList.replace('text-cyan-300', 'text-slate-300');
    } else {
      label.innerText = 'Sign In';
      btn.classList.replace('text-slate-300', 'text-cyan-300');
    }
  }
}

export function openLoginModal() {
  openModal({
    title: 'Authenticate OmiMind Session',
    subtitle: 'Enter your configured API Secret Key to establish an authenticated session.',
    contentHtml: `
      <div class="space-y-4">
        <p class="text-xs text-slate-400">
          Backend API endpoints are protected with strict authorization. Submitting your API key sets a secure, HttpOnly, SameSite session cookie. Credentials are never stored in browser localStorage.
        </p>
        <div>
          <label for="input-api-secret" class="block text-xs font-semibold text-slate-300 mb-1.5">API Secret Key</label>
          <input
            id="input-api-secret"
            type="password"
            placeholder="Enter API_SECRET_KEY"
            autocomplete="current-password"
            class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-white/10 text-white text-sm focus:outline-none focus:border-cyan-500/50"
          />
        </div>
      </div>
    `,
    actionsHtml: `
      <button id="btn-cancel-login" class="px-3.5 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white transition">Cancel</button>
      <button id="btn-submit-login" class="px-4 py-2 rounded-xl text-xs font-semibold bg-cyan-500 hover:bg-cyan-400 text-slate-950 transition flex items-center gap-1.5">Sign In</button>
    `,
  });

  const submitBtn = document.getElementById('btn-submit-login');
  const inputEl = document.getElementById('input-api-secret');
  const cancelBtn = document.getElementById('btn-cancel-login');

  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  const doLogin = async () => {
    const key = inputEl?.value?.trim();
    if (!key) {
      showToast('Please enter your API secret key', 'warning');
      return;
    }
    submitBtn.disabled = true;
    submitBtn.innerText = 'Authenticating...';
    try {
      await api.login(key);
      showToast('Authenticated successfully', 'success');
      closeModal();
      updateAuthButtonState(true);
      await refreshAppData();
    } catch (err) {
      showToast(err.message || 'Authentication failed', 'error');
      submitBtn.disabled = false;
      submitBtn.innerText = 'Sign In';
    }
  };

  if (submitBtn) submitBtn.addEventListener('click', doLogin);
  if (inputEl) {
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') doLogin();
    });
  }
}

async function bootstrap() {
  initNav();

  // Check authentication status and load initial data
  const auth = await api.checkAuthStatus().catch(() => ({ authenticated: false }));
  updateAuthButtonState(auth.authenticated);

  await refreshAppData();

  // Setup Audio Engine
  voiceEngine = setupVoiceCapture({
    onTranscript: (text) => {
      const input = document.getElementById('modal-voice-input') || document.getElementById('live-voice-input');
      if (input) {
        input.value = text;
        input.scrollTop = input.scrollHeight;
      }
    },
    onStatus: (status) => {
      const isListening = status.includes('Listening');
      setState({ isRecording: isListening });

      // Update mic button texts across DOM
      const homeMicText = document.getElementById('home-mic-text');
      if (homeMicText) homeMicText.innerText = isListening ? 'Stop Recording' : 'Record Voice';

      const topMicBadge = document.getElementById('top-mic-badge');
      if (topMicBadge) {
        if (isListening) {
          topMicBadge.classList.remove('hidden');
        } else {
          topMicBadge.classList.add('hidden');
        }
      }
    },
    onError: (err) => {
      showToast(err.message || 'Microphone error', 'warning');
    }
  });

  // Setup Global Ambient Waveform
  stopWaveform = initWaveform(
    'ambient-waveform',
    () => voiceEngine?.getAudioFrequencyData?.(),
    () => getState().isRecording
  );

  // Global event delegation for Mic triggers and Quick Voice Memo
  document.addEventListener('click', async (e) => {
    // 0. Auth toggle button
    const authBtn = e.target.closest('#btn-auth-toggle');
    if (authBtn) {
      e.preventDefault();
      const auth = await api.checkAuthStatus().catch(() => ({ authenticated: false }));
      if (auth.authenticated) {
        await api.logout();
        showToast('Logged out successfully', 'info');
        updateAuthButtonState(false);
      } else {
        openLoginModal();
      }
      return;
    }

    // 1. Mic Toggle button
    const micBtn = e.target.closest('#btn-home-mic, #btn-top-mic, #btn-mic');
    if (micBtn) {
      e.preventDefault();
      if (!getState().isRecording) {
        // Open live voice recording modal
        openVoiceCaptureModal();
      }
      await voiceEngine.toggle();
      return;
    }

    // 1b. Type Note / Direct Ingest modal button
    const typeBtn = e.target.closest('#btn-home-type, #btn-top-type, #btn-ask-type, .btn-open-type-memo');
    if (typeBtn) {
      e.preventDefault();
      openTypeMemoModal();
      return;
    }

    // 2. Refresh Waveform canvas if user navigated to Home
    if (e.target.closest('[data-route="home"], [data-mobile-route="home"]')) {
      setTimeout(() => {
        if (stopWaveform) stopWaveform();
        stopWaveform = initWaveform(
          'ambient-waveform',
          () => voiceEngine?.getAudioFrequencyData?.(),
          () => getState().isRecording
        );
      }, 100);
    }
  });

  // Listen for unauthorized responses across all views
  window.addEventListener('omimind:unauthorized', () => {
    updateAuthButtonState(false);
    if (!document.getElementById('input-api-secret')) {
      openLoginModal();
    }
  });

  // Global Ctrl/Cmd + K shortcut for instant ambient memory recall
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      if (!window.location.hash.startsWith('#ask')) {
        navigate('ask');
      }
      setTimeout(() => {
        const askInput = document.getElementById('ask-input') || document.getElementById('home-ask-input');
        if (askInput) {
          askInput.focus();
          askInput.select?.();
        }
      }, 50);
    }
  });

  // Start client router
  initRouter();
}

function openVoiceCaptureModal() {
  openModal({
    title: 'Live Omi Voice Capture',
    subtitle: 'Speak into your microphone or enter voice memo transcript to index into Qdrant.',
    contentHtml: `
      <div class="space-y-4">
        <div class="flex items-center justify-between text-xs font-mono-tech">
          <span class="text-cyan-300 flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
            Listening (Web Speech API active)...
          </span>
          <span class="text-slate-400">Speaker: User</span>
        </div>
        <textarea 
          id="modal-voice-input" 
          rows="4" 
          placeholder="Speak or type: 'My live Omi verification phrase is Aurora 4821 and I will finalize the sprint deliverables by Friday...'"
          class="w-full p-3.5 rounded-xl bg-slate-900 border border-white/10 text-xs font-mono-tech text-white focus:outline-none focus:border-cyan-500 custom-scrollbar resize-none"
        ></textarea>
        <div class="p-3 rounded-lg bg-slate-950 border border-white/5 text-[11px] font-mono-tech text-slate-400">
          Utterances will be embedded into Qdrant collection <code class="text-cyan-300">omi_ambient_memory</code> and synthesized via Lyzr multi-agent swarm.
        </div>
      </div>
    `,
    actionsHtml: `
      <button id="modal-voice-cancel" class="px-3.5 py-2 rounded-xl text-xs text-slate-400 hover:text-white transition">
        Cancel
      </button>
      <button id="modal-voice-stream" class="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-semibold text-xs shadow-md transition flex items-center gap-1.5">
        <span>Vectorize & Run Swarm</span>
      </button>
    `
  });

  const cancelBtn = document.getElementById('modal-voice-cancel');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      if (getState().isRecording) voiceEngine.toggle();
      closeModal();
    });
  }

  const streamBtn = document.getElementById('modal-voice-stream');
  if (streamBtn) {
    streamBtn.addEventListener('click', async () => {
      const input = document.getElementById('modal-voice-input');
      const text = input ? input.value.trim() : '';
      if (!text) {
        showToast('Please speak or type a transcript first.', 'warning');
        return;
      }

      if (getState().isRecording) {
        await voiceEngine.toggle();
      }

      streamBtn.disabled = true;
      streamBtn.innerText = 'Streaming to Qdrant...';

      try {
        await api.streamPipeline('/api/custom-voice-stream', {
          transcript: text,
          speaker: 'Voice Input',
          title: 'Live Ambient Sync'
        }, {
          onEvent: (event) => {
            addPipelineEvent(event);
          },
          onError: (err) => {
            showToast('Voice streaming error: ' + err.message, 'warning');
          },
          onComplete: async (dossier) => {
            setState({ activeDossier: dossier });
            showToast('Voice memo vectorized and indexed into Qdrant!');
            closeModal();
            // Refresh memories
            const memData = await api.fetchMemories(30);
            setState({ memories: memData.memories || [] });
          }
        });
      } catch (err) {
        showToast('Submission error: ' + err.message, 'warning');
      } finally {
        streamBtn.disabled = false;
      }
    });
  }
}

export function openTypeMemoModal() {
  openModal({
    title: 'Direct Note & Meeting Data Input',
    subtitle: 'Type or paste transcripts, notes, or memos directly into Qdrant vector memory and trigger Lyzr multi-agent swarm.',
    contentHtml: `
      <div class="space-y-4">
        <!-- Quick Preset Templates -->
        <div>
          <div class="text-[11px] font-mono-tech text-slate-400 mb-1.5 flex items-center justify-between">
            <span>Quick 1-Click Templates:</span>
            <span class="text-indigo-400 font-medium">Click to populate</span>
          </div>
          <div class="flex flex-wrap gap-1.5">
            <button type="button" class="btn-memo-preset px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-white/10 text-[11px] text-cyan-300 hover:text-white transition"
              data-speaker="Masood"
              data-title="Executive AI Infrastructure Review"
              data-text="During the executive sync, Masood and the leadership committee approved three hundred and fifty thousand dollars ($350,000) for our Q4 AI infrastructure and Project Horizon.">
              💼 Project Horizon ($350k)
            </button>
            <button type="button" class="btn-memo-preset px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-white/10 text-[11px] text-indigo-300 hover:text-white transition"
              data-speaker="DevOps Lead"
              data-title="Infrastructure & Cloud Sync"
              data-text="The DevOps engineering team confirmed the Tokyo server migration is scheduled for October 24th at 02:00 UTC. Rollback plans are verified in staging.">
              🗼 Tokyo Migration (Oct 24)
            </button>
            <button type="button" class="btn-memo-preset px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-white/10 text-[11px] text-amber-300 hover:text-white transition"
              data-speaker="Alex"
              data-title="Sprint Planning & Deliverables"
              data-text="Action item: Ken must prepare the security audit report by Thursday 5 PM before the investor demo. Sarah will coordinate customer rollout.">
              ⚡ Sprint Action Items
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-slate-400 text-xs font-mono-tech mb-1">Speaker Name</label>
            <input 
              id="modal-type-speaker" 
              type="text" 
              value="User"
              class="w-full px-3 py-2 rounded-xl bg-slate-900 border border-white/10 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono-tech"
              placeholder="e.g. Masood, Sarah, Alex"
            />
          </div>
          <div>
            <label class="block text-slate-400 text-xs font-mono-tech mb-1">Meeting / Memo Title</label>
            <input 
              id="modal-type-title" 
              type="text" 
              value="Direct Ambient Memo"
              class="w-full px-3 py-2 rounded-xl bg-slate-900 border border-white/10 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono-tech"
              placeholder="e.g. Executive Sync, Sprint Planning"
            />
          </div>
        </div>

        <div>
          <label class="block text-slate-400 text-xs font-mono-tech mb-1">Transcript / Note Content</label>
          <textarea 
            id="modal-type-input" 
            rows="5" 
            placeholder="Type or paste conversation transcript or notes here...&#10;&#10;e.g. In today's meeting we approved a budget of $350k for Project Horizon and scheduled the Tokyo migration for October 24."
            class="w-full p-3.5 rounded-xl bg-slate-900 border border-white/10 text-xs font-mono-tech text-white focus:outline-none focus:border-cyan-500 custom-scrollbar resize-none"
          ></textarea>
        </div>

        <div class="p-3 rounded-lg bg-slate-950 border border-white/5 text-[11px] font-mono-tech text-slate-400 flex items-center justify-between">
          <span>Target: <code class="text-cyan-300">omi_ambient_memory</code> (Qdrant Cloud)</span>
          <span class="text-indigo-400">Lyzr Multi-Agent Swarm</span>
        </div>
      </div>
    `,
    actionsHtml: `
      <button id="modal-type-cancel" class="px-3.5 py-2 rounded-xl text-xs text-slate-400 hover:text-white transition">
        Cancel
      </button>
      <button id="modal-type-stream" class="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-semibold text-xs shadow-md transition flex items-center gap-1.5">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
        <span>Vectorize & Run Swarm</span>
      </button>
    `
  });

  const cancelBtn = document.getElementById('modal-type-cancel');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', closeModal);
  }

  // Preset buttons handler
  document.querySelectorAll('.btn-memo-preset').forEach(presetBtn => {
    presetBtn.addEventListener('click', () => {
      const spk = presetBtn.getAttribute('data-speaker') || 'User';
      const ttl = presetBtn.getAttribute('data-title') || 'Direct Memo';
      const txt = presetBtn.getAttribute('data-text') || '';
      const spkInput = document.getElementById('modal-type-speaker');
      const ttlInput = document.getElementById('modal-type-title');
      const txtInput = document.getElementById('modal-type-input');
      if (spkInput) spkInput.value = spk;
      if (ttlInput) ttlInput.value = ttl;
      if (txtInput) {
        txtInput.value = txt;
        txtInput.focus();
      }
    });
  });

  const streamBtn = document.getElementById('modal-type-stream');
  if (streamBtn) {
    streamBtn.addEventListener('click', async () => {
      const input = document.getElementById('modal-type-input');
      const text = input ? input.value.trim() : '';
      if (!text) {
        showToast('Please type note or memo text first.', 'warning');
        return;
      }
      const speaker = (document.getElementById('modal-type-speaker')?.value || 'User').trim();
      const title = (document.getElementById('modal-type-title')?.value || 'Direct Note').trim();

      streamBtn.disabled = true;
      streamBtn.innerText = 'Streaming to Qdrant...';

      try {
        await api.streamPipeline('/api/custom-voice-stream', {
          transcript: text,
          speaker: speaker || 'User',
          title: title || 'Direct Ambient Note'
        }, {
          onEvent: (event) => {
            addPipelineEvent(event);
          },
          onError: (err) => {
            showToast('Note streaming error: ' + err.message, 'warning');
          },
          onComplete: async (dossier) => {
            setState({ activeDossier: dossier });
            showToast('Note vectorized and indexed into Qdrant memory!');
            closeModal();
            // Refresh memories in state
            const memData = await api.fetchMemories(30);
            setState({ memories: memData.memories || [] });
          }
        });
      } catch (err) {
        showToast('Submission error: ' + err.message, 'warning');
      } finally {
        streamBtn.disabled = false;
      }
    });
  }
}

// Start application when DOM is ready
document.addEventListener('DOMContentLoaded', bootstrap);
