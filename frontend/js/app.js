/**
 * app.js - Main Application Bootstrapper for OMIMIND 2.0
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
import { getSession, signIn, signOut, signUp, resetPassword, updatePassword } from './supabase.js';

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

function renderLanding() {
  const landing = document.getElementById('public-landing');
  if (!landing) return;
  document.getElementById('app-shell')?.classList.add('hidden');
  landing.classList.remove('hidden');
  landing.innerHTML = `<div class="min-h-screen bg-[#060811] text-slate-100"><div class="mx-auto max-w-7xl px-6 py-6 lg:px-10"><header class="flex items-center justify-between"><a href="#" class="flex items-center gap-3"><span class="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-tr from-cyan-400 to-indigo-600 font-bold">Ω</span><span class="text-lg font-extrabold tracking-tight">OMIMIND</span></a><button id="landing-signin" class="rounded-xl border border-cyan-400/40 bg-cyan-400/10 px-4 py-2 text-sm font-semibold text-cyan-200">Sign in</button></header><main class="grid items-center gap-12 pb-20 pt-20 lg:grid-cols-[1.08fr_.92fr]"><section><p class="mb-5 inline-flex rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[.2em] text-cyan-200">Voice → memory → momentum</p><h1 class="max-w-3xl text-5xl font-extrabold leading-[1.03] tracking-tight sm:text-6xl">Make every conversation useful after it ends.</h1><p class="mt-6 max-w-2xl text-lg leading-8 text-slate-300">OMIMIND turns Omi voice conversations into searchable memory, decisions, action items, and reviewable follow-up drafts with a visible Lyzr multi-agent workflow.</p><div class="mt-8 flex flex-wrap gap-3"><button id="landing-cta" class="rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 px-5 py-3 text-sm font-bold text-white">Try a sample workflow</button><button id="landing-learn" class="rounded-xl border border-white/10 px-5 py-3 text-sm font-semibold text-slate-200">See how it works</button></div><p class="mt-5 text-xs text-slate-500">Create your own workspace. Demo telemetry stays labeled until a live Omi connection is active.</p></section><div class="rounded-3xl border border-white/10 bg-slate-950/70 p-5 shadow-2xl"><div class="mb-4 flex items-center justify-between"><span class="text-xs font-bold uppercase tracking-[.18em] text-slate-400">Sample meeting preview</span><span class="rounded-full bg-emerald-400/10 px-2 py-1 text-[10px] font-semibold text-emerald-300">Ready to explore</span></div><div class="space-y-3"><div class="rounded-2xl border border-cyan-400/20 bg-cyan-400/5 p-4"><p class="text-sm font-semibold">Q4 Product Strategy Sync</p><p class="mt-1 text-xs text-slate-400">Omi capture → Qdrant evidence → Lyzr swarm → user-reviewed drafts</p></div><div class="grid grid-cols-2 gap-3 text-xs"><div class="rounded-2xl bg-white/5 p-4"><p class="text-slate-400">Decisions</p><p class="mt-2 text-xl font-bold text-white">04</p></div><div class="rounded-2xl bg-white/5 p-4"><p class="text-slate-400">Action items</p><p class="mt-2 text-xl font-bold text-white">07</p></div></div><div class="rounded-2xl border border-white/10 p-4 text-[11px] text-slate-400"><p class="text-cyan-200">● Agent trace visible during processing</p><p class="mt-2">Memory Recall <span class="float-right text-emerald-300">complete</span></p><p>Meeting Analyst <span class="float-right text-emerald-300">complete</span></p><p>Action Extractor <span class="float-right text-amber-300">review</span></p></div></div></div></main><section id="landing-details" class="grid gap-5 pb-20 md:grid-cols-3"><article class="rounded-2xl border border-white/10 bg-white/[.03] p-5"><p class="text-xs font-bold uppercase tracking-[.18em] text-cyan-300">The problem</p><h2 class="mt-3 text-lg font-bold">Important commitments disappear into conversation.</h2><p class="mt-2 text-sm leading-6 text-slate-400">Teams remember fragments, lose owners, and spend hours reconstructing what was actually decided.</p></article><article class="rounded-2xl border border-white/10 bg-white/[.03] p-5"><p class="text-xs font-bold uppercase tracking-[.18em] text-indigo-300">The solution</p><h2 class="mt-3 text-lg font-bold">A memory layer for work that keeps context attached.</h2><p class="mt-2 text-sm leading-6 text-slate-400">OMIMIND grounds outputs in the conversation, then lets you inspect and approve what happens next.</p></article><article class="rounded-2xl border border-white/10 bg-white/[.03] p-5"><p class="text-xs font-bold uppercase tracking-[.18em] text-emerald-300">The loop</p><h2 class="mt-3 text-lg font-bold">Omi → Qdrant → Lyzr → your review.</h2><p class="mt-2 text-sm leading-6 text-slate-400">Voice becomes searchable evidence, specialist agents reason over it, and drafts remain user-controlled.</p></article></section></div></div>`;
  document.getElementById('landing-signin')?.addEventListener('click', openLoginModal);
  document.getElementById('landing-cta')?.addEventListener('click', openLoginModal);
  document.getElementById('landing-learn')?.addEventListener('click', () => document.getElementById('landing-details')?.scrollIntoView({ behavior: 'smooth' }));
}

export function openLoginModal() {
  openModal({
    title: 'Enter your OMIMIND workspace',
    subtitle: 'Create an account or sign in with your verified email.',
    contentHtml: `
      <div class="space-y-4">
        <div>
          <label for="input-auth-email" class="block text-xs font-semibold text-slate-300 mb-1.5">Email</label><input id="input-auth-email" type="email" placeholder="you@example.com" autocomplete="email" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-white/10 text-white text-sm focus:outline-none focus:border-cyan-500/50" />
        </div>
        <div><label for="input-auth-password" class="block text-xs font-semibold text-slate-300 mb-1.5">Password</label><input id="input-auth-password" type="password" placeholder="At least 8 characters" autocomplete="current-password" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-white/10 text-white text-sm focus:outline-none focus:border-cyan-500/50" /></div>
        <div class="flex items-center justify-between text-xs"><button id="btn-auth-mode" class="text-cyan-300 hover:text-cyan-200">Create an account</button><button id="btn-auth-reset" class="text-slate-400 hover:text-white">Forgot password?</button></div>
      </div>
    `,
    actionsHtml: `
      <button id="btn-cancel-login" class="px-3.5 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white transition">Cancel</button>
      <button id="btn-submit-login" class="px-4 py-2 rounded-xl text-xs font-semibold bg-cyan-500 hover:bg-cyan-400 text-slate-950 transition flex items-center gap-1.5">Sign In</button>
    `,
  });

  const submitBtn = document.getElementById('btn-submit-login');
  const inputEl = document.getElementById('input-auth-password');
  const emailEl = document.getElementById('input-auth-email');
  const cancelBtn = document.getElementById('btn-cancel-login');
  const modeBtn = document.getElementById('btn-auth-mode');
  let signupMode = false;

  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  modeBtn?.addEventListener('click', () => { signupMode = !signupMode; modeBtn.innerText = signupMode ? 'Already have an account?' : 'Create an account'; submitBtn.innerText = signupMode ? 'Create account' : 'Sign In'; });

  const doLogin = async () => {
    const email = emailEl?.value?.trim();
    const password = inputEl?.value || '';
    if (!email || !password) {
      showToast('Enter an email and password.', 'warning');
      return;
    }
    submitBtn.disabled = true;
    submitBtn.innerText = 'Authenticating...';
    try {
      if (signupMode) {
        const result = await signUp(email, password);
        if (!result.session) {
          showToast('Account created. Check your inbox and verify your email before signing in.', 'success');
          submitBtn.disabled = false;
          submitBtn.innerText = 'Create account';
          return;
        }
        showToast('Account created.', 'success');
      } else {
        await signIn(email, password);
        showToast('Welcome back.', 'success');
      }
      closeModal();
      document.getElementById('public-landing')?.classList.add('hidden');
      document.getElementById('app-shell')?.classList.remove('hidden');
      initNav();
      updateAuthButtonState(true);
      await refreshAppData();
      initRouter();
    } catch (err) {
      showToast(err.message || 'Authentication failed', 'error');
      submitBtn.disabled = false;
      submitBtn.innerText = signupMode ? 'Create account' : 'Sign In';
    }
  };

  if (submitBtn) submitBtn.addEventListener('click', doLogin);
  if (inputEl) {
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') doLogin();
    });
  }
  document.getElementById('btn-auth-reset')?.addEventListener('click', async () => { const email = emailEl?.value?.trim(); if (!email) return showToast('Enter your email first.', 'warning'); try { await resetPassword(email); showToast('Password reset email sent.', 'success'); } catch (err) { showToast(err.message, 'error'); } });
}

function openRecoveryModal() {
  openModal({
    title: 'Set a new OMIMIND password',
    subtitle: 'Choose a new password for this verified account.',
    contentHtml: '<label for="recovery-password" class="block text-xs font-semibold text-slate-300 mb-1.5">New password</label><input id="recovery-password" type="password" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-white/10 text-white text-sm" placeholder="At least 8 characters" />',
    actionsHtml: '<button id="recovery-submit" class="px-4 py-2 rounded-xl text-xs font-semibold bg-cyan-500 text-slate-950">Update password</button>',
  });
  document.getElementById('recovery-submit')?.addEventListener('click', async () => {
    const password = document.getElementById('recovery-password')?.value || '';
    if (password.length < 8) return showToast('Use at least 8 characters.', 'warning');
    try { await updatePassword(password); closeModal(); showToast('Password updated.', 'success'); } catch (err) { showToast(err.message, 'error'); }
  });
}

async function bootstrap() {
  const supabaseSession = await getSession().catch(() => ({ session: null }));
  const auth = supabaseSession.session ? { authenticated: true } : await api.checkAuthStatus().catch(() => ({ authenticated: false }));
  if (!auth.authenticated) {
    renderLanding();
    updateAuthButtonState(false);
    return;
  }
  document.getElementById('public-landing')?.classList.add('hidden');
  document.getElementById('app-shell')?.classList.remove('hidden');
  initNav();
  updateAuthButtonState(true);
  await refreshAppData();
  if (window.location.hash.includes('type=recovery')) openRecoveryModal();

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
        await signOut();
        showToast('Logged out successfully', 'info');
        updateAuthButtonState(false);
        renderLanding();
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
    if (!document.getElementById('input-auth-email')) {
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
