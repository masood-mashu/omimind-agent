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
  landing.innerHTML = `
    <div class="min-h-screen bg-[#090d14] text-slate-100 selection:bg-teal-500/30 selection:text-teal-200">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-6">
        
        <!-- Header -->
        <header class="flex items-center justify-between py-2 border-b border-white/5">
          <a href="#" class="flex items-center gap-2.5 group">
            <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-teal-400 via-cyan-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-teal-500/20 group-hover:scale-105 transition">
              <span class="text-sm font-bold text-slate-950">Ω</span>
            </div>
            <div>
              <div class="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
                <span>OMIMIND</span>
                <span class="text-[9px] px-1.5 py-0.5 rounded bg-teal-500/10 text-teal-300 font-mono-tech border border-teal-500/20">2.0</span>
              </div>
              <p class="text-[10px] text-slate-400 font-mono-tech leading-none mt-0.5">Ambient Voice Intelligence</p>
            </div>
          </a>

          <nav class="flex items-center gap-3 sm:gap-6 text-xs text-slate-400">
            <a href="#landing-how" class="hidden sm:inline hover:text-white transition">How it works</a>
            <a href="#landing-features" class="hidden md:inline hover:text-white transition">Features</a>
            <a href="#landing-privacy" class="hidden lg:inline hover:text-white transition">Privacy</a>
            <button id="landing-signin" class="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white border border-white/10 hover:border-white/20 hover:bg-white/5 transition">
              Sign in
            </button>
            <button id="landing-cta" class="btn-mint-cta text-xs">
              <span>Start free</span>
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
            </button>
          </nav>
        </header>

        <!-- Hero Section -->
        <main class="grid items-center gap-12 pt-16 pb-20 lg:grid-cols-[1.05fr_.95fr]">
          
          <!-- Hero Copy -->
          <section class="space-y-6">
            <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-teal-500/10 border border-teal-500/20 text-teal-300 text-[11px] font-mono-tech">
              <span class="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse"></span>
              <span>YOUR AMBIENT AI CHIEF OF STAFF</span>
            </div>

            <h1 class="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-[1.06]">
              Your AI<br>
              <span class="text-transparent bg-clip-text bg-gradient-to-r from-teal-200 via-cyan-200 to-indigo-300">second mind.</span>
            </h1>

            <p class="text-lg sm:text-xl font-medium text-slate-300 leading-snug">
              Remember everything. Find anything. Miss nothing.
            </p>

            <p class="text-sm sm:text-base text-slate-400 max-w-xl leading-relaxed">
              Your work has too many conversations. OMIMIND brings your meetings, ambient spoken thoughts, and commitments into one place — so you can find what matters and decide what happens next.
            </p>

            <div class="flex flex-wrap items-center gap-3 pt-2">
              <button id="landing-cta-hero" class="btn-mint-cta text-sm">
                <span>Start free</span>
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
              </button>
              <button id="landing-learn" class="px-4 py-2.5 rounded-xl text-sm font-medium text-slate-300 hover:text-white transition flex items-center gap-1.5 hover:bg-white/5">
                <span>See how it works</span>
                <span aria-hidden="true">↓</span>
              </button>
            </div>

            <p class="text-[11px] text-slate-500 font-mono-tech pt-2">
              Single-user demo • Omi wearable capture • Human review before actions execute.
            </p>
          </section>

          <!-- Hero Workspace Showcase Mockup (Inspired by omnimindai.app workspace) -->
          <div class="omimind-mockup-frame p-6 space-y-4">
            
            <!-- Window Top Bar -->
            <div class="flex items-center justify-between text-xs pb-3 border-b border-white/5 font-mono-tech">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-teal-400 animate-pulse"></span>
                <strong class="text-white font-semibold">Today</strong>
                <span class="text-slate-500">•</span>
                <span class="text-teal-300">OMIMIND Workspace</span>
              </div>
              <span class="px-2 py-0.5 rounded bg-white/5 text-[10px] text-slate-400">Sample meeting ready</span>
            </div>

            <!-- Workspace Body Header -->
            <div class="space-y-1">
              <h2 class="text-xl font-bold text-white tracking-tight">What matters today</h2>
              <p class="text-xs text-slate-400">One place for the commitments and decisions you make.</p>
            </div>

            <!-- Mock Search Box -->
            <div class="flex items-center gap-2.5 px-3.5 py-3 rounded-xl bg-slate-900/90 border border-white/10 text-xs text-slate-400 cursor-pointer hover:border-teal-500/30 transition">
              <svg class="w-4 h-4 text-teal-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
              <span class="flex-1">Ask about your saved meetings & decisions...</span>
              <svg class="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
            </div>

            <!-- "Needs Your Review" Attention Card -->
            <div class="attention-review-box p-4 space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-mono-tech uppercase tracking-wider text-teal-300 font-bold">Needs your review</span>
                <span class="text-[10px] font-mono-tech text-amber-300">High priority</span>
              </div>
              <div class="flex items-start gap-2.5">
                <svg class="w-4 h-4 text-teal-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>
                <div>
                  <h3 class="text-xs font-bold text-white">Check an important commitment</h3>
                  <p class="text-[11px] text-slate-300 mt-0.5">Confirm Q3 cloud budget approval before dispatching Jira ticket.</p>
                </div>
              </div>
              <div class="pt-1 flex items-center justify-between text-[11px]">
                <span class="text-teal-400 font-medium flex items-center gap-1 hover:underline cursor-pointer">
                  Review commitment <span aria-hidden="true">→</span>
                </span>
                <span class="text-[10px] text-slate-500 font-mono-tech">AI draft pending</span>
              </div>
            </div>

            <!-- Voice Thought Snippet Card -->
            <div class="p-3.5 rounded-xl bg-slate-900/60 border border-white/5 flex items-start gap-3">
              <div class="w-8 h-8 rounded-lg bg-teal-500/10 flex items-center justify-center text-teal-400 flex-shrink-0">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z"/></svg>
              </div>
              <div class="text-xs space-y-0.5">
                <strong class="text-slate-200">A thought to keep</strong>
                <p class="text-slate-400 italic">“Let's push the API v2 migration to Thursday and assign tickets to Alex.”</p>
                <p class="text-[10px] text-slate-500 font-mono-tech">Example Omi wearable transcript</p>
              </div>
            </div>

            <!-- Bottom Tabs -->
            <div class="pt-2 border-t border-white/5 flex items-center justify-between text-[11px] text-slate-400 font-mono-tech">
              <span class="flex items-center gap-1.5"><span class="text-teal-400">📄</span> Transcripts</span>
              <span class="flex items-center gap-1.5"><span class="text-indigo-400">⚡</span> Lyzr Swarm</span>
              <span class="flex items-center gap-1.5"><span class="text-amber-400">📋</span> Jira & Calendar</span>
            </div>

          </div>

        </main>

        <!-- Problem Statement & Entity Filter Pills -->
        <section class="text-center py-16 border-t border-white/5 space-y-4 max-w-3xl mx-auto">
          <p class="text-[11px] font-mono-tech uppercase tracking-widest text-teal-400 font-semibold">Less searching. More execution.</p>
          <h2 class="text-2xl sm:text-4xl font-bold text-white tracking-tight">
            Work is scattered.<br>What matters should be connected.
          </h2>
          <p class="text-sm sm:text-base text-slate-400 leading-relaxed">
            Spoken agreements vanish into thin air. Important deadlines get buried in chat. Give your conversations a continuous memory layer where you can find them and act before you forget.
          </p>
          <div class="flex flex-wrap items-center justify-center gap-2 pt-2 text-xs font-mono-tech">
            <span class="query-pill">🎙️ Ambient Audio</span>
            <span class="query-pill">📄 Meeting Transcripts</span>
            <span class="query-pill">🧠 384d Dense Memory</span>
            <span class="query-pill">⚡ Action Commitments</span>
            <span class="query-pill">📅 Calendar Invites</span>
          </div>
        </section>

        <!-- 3-Step Numbered Workflow -->
        <section id="landing-how" class="py-16 border-t border-white/5 space-y-8">
          <div class="text-center space-y-2 max-w-xl mx-auto">
            <p class="text-[11px] font-mono-tech uppercase tracking-widest text-teal-400 font-semibold">How it works</p>
            <h2 class="text-2xl sm:text-3xl font-bold text-white tracking-tight">Capture. Understand. Act.</h2>
            <p class="text-xs sm:text-sm text-slate-400">Start with one conversation you do not want to lose track of.</p>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="p-6 rounded-2xl bg-slate-900/50 border border-white/5 space-y-3 relative overflow-hidden group hover:border-teal-500/30 transition">
              <span class="text-3xl font-mono-tech font-bold text-teal-400/30 group-hover:text-teal-400/60 transition">01</span>
              <h3 class="text-base font-bold text-white">Hand it over</h3>
              <p class="text-xs sm:text-sm text-slate-400 leading-relaxed">
                Stream ambient speech from Omi wearable, record via microphone, or type a note directly. Every utterance is captured with full context.
              </p>
              <div class="pt-3 flex items-center gap-2 text-[11px] font-mono-tech text-teal-300">
                <span>Omi Ingress & Bluetooth</span>
              </div>
            </div>

            <div class="p-6 rounded-2xl bg-slate-900/50 border border-white/5 space-y-3 relative overflow-hidden group hover:border-indigo-500/30 transition">
              <span class="text-3xl font-mono-tech font-bold text-indigo-400/30 group-hover:text-indigo-400/60 transition">02</span>
              <h3 class="text-base font-bold text-white">Make it useful</h3>
              <p class="text-xs sm:text-sm text-slate-400 leading-relaxed">
                Qdrant Cloud indexes utterances into 384d vectors. Lyzr Agent Studio swarms analyze commitments, decisions, and speaker attributions.
              </p>
              <div class="pt-3 flex items-center gap-2 text-[11px] font-mono-tech text-indigo-300">
                <span>Qdrant + FastEmbed</span>
              </div>
            </div>

            <div class="p-6 rounded-2xl bg-slate-900/50 border border-white/5 space-y-3 relative overflow-hidden group hover:border-amber-500/30 transition">
              <span class="text-3xl font-mono-tech font-bold text-amber-400/30 group-hover:text-amber-400/60 transition">03</span>
              <h3 class="text-base font-bold text-white">Choose the next step</h3>
              <p class="text-xs sm:text-sm text-slate-400 leading-relaxed">
                Review extracted drafts before dispatching. Generate executive markdown email memos, structured Jira backlog tickets, and 1-click Google Calendar invites.
              </p>
              <div class="pt-3 flex items-center gap-2 text-[11px] font-mono-tech text-amber-300">
                <span>User-Controlled Dispatch</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Split Feature: Ask Your Meetings -->
        <section id="landing-features" class="grid items-center gap-12 py-16 border-t border-white/5 lg:grid-cols-2">
          <div class="space-y-4">
            <p class="text-[11px] font-mono-tech uppercase tracking-widest text-teal-400 font-semibold">Ask your conversations</p>
            <h2 class="text-2xl sm:text-4xl font-bold text-white tracking-tight">
              A question.<br>Your context.
            </h2>
            <p class="text-sm sm:text-base text-slate-400 leading-relaxed">
              Ask about past meetings, technical agreements, or team commitments. Every answer is grounded directly in stored memory points with transparent source attribution.
            </p>
            <button id="landing-try-ask" class="text-xs font-semibold text-teal-300 hover:text-teal-200 flex items-center gap-1.5 transition">
              <span>Open Ask OMIMIND in demo</span>
              <span aria-hidden="true">→</span>
            </button>
          </div>

          <div class="space-y-3 p-6 rounded-2xl bg-slate-900/60 border border-white/5">
            <p class="text-[11px] text-slate-400 font-mono-tech mb-3">Example questions answered from grounded memory:</p>
            <div class="query-pill w-full justify-between cursor-pointer hover:border-teal-500/40">
              <span class="flex items-center gap-2">
                <svg class="w-3.5 h-3.5 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
                <span>What budget was approved for Project Horizon?</span>
              </span>
              <span class="text-[10px] text-teal-300 font-mono-tech">$120,000 confirmed</span>
            </div>
            <div class="query-pill w-full justify-between cursor-pointer hover:border-teal-500/40">
              <span class="flex items-center gap-2">
                <svg class="w-3.5 h-3.5 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
                <span>What did Sarah commit to regarding API v2?</span>
              </span>
              <span class="text-[10px] text-teal-300 font-mono-tech">Thursday deadline</span>
            </div>
            <div class="query-pill w-full justify-between cursor-pointer hover:border-teal-500/40">
              <span class="flex items-center gap-2">
                <svg class="w-3.5 h-3.5 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
                <span>Show all unassigned action items from yesterday</span>
              </span>
              <span class="text-[10px] text-amber-300 font-mono-tech">3 items flagged</span>
            </div>
            <small class="block text-[10px] text-slate-500 pt-2">Responses depend on conversations saved in your workspace.</small>
          </div>
        </section>

        <!-- Privacy & Architecture Section -->
        <section id="landing-privacy" class="py-16 border-t border-white/5 space-y-6">
          <div class="p-8 rounded-2xl bg-slate-900/60 border border-white/5 max-w-3xl mx-auto space-y-4">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-xl bg-teal-500/10 flex items-center justify-center text-teal-400">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>
              </div>
              <div>
                <p class="text-[11px] font-mono-tech uppercase tracking-widest text-teal-400 font-semibold">Privacy & Security, Explained Plainly</p>
                <h3 class="text-lg font-bold text-white">Your data. Transparent controls.</h3>
              </div>
            </div>
            <p class="text-xs sm:text-sm text-slate-400 leading-relaxed">
              Utterances are vectorized into dense 384-dimensional embeddings via FastEmbed and stored securely in Qdrant Cloud. Lyzr Agent Studio swarms analyze transcripts with user-controlled review before any Jira ticket or email is drafted. All webhook payloads support HMAC-SHA256 signature verification and replay prevention.
            </p>
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2 text-xs font-mono-tech text-slate-400">
              <div class="p-2.5 rounded-lg bg-black/30 border border-white/5">
                <span class="text-teal-300 font-semibold">Qdrant Cloud</span>
                <p class="text-[10px] text-slate-500 mt-0.5">Isolated vector collection</p>
              </div>
              <div class="p-2.5 rounded-lg bg-black/30 border border-white/5">
                <span class="text-indigo-300 font-semibold">Lyzr Studio</span>
                <p class="text-[10px] text-slate-500 mt-0.5">Manager & recall swarm</p>
              </div>
              <div class="p-2.5 rounded-lg bg-black/30 border border-white/5 col-span-2 sm:col-span-1">
                <span class="text-emerald-300 font-semibold">User Review</span>
                <p class="text-[10px] text-slate-500 mt-0.5">Deterministic approvals</p>
              </div>
            </div>
          </div>
        </section>

        <!-- Final CTA Banner -->
        <section class="text-center py-16 border-t border-white/5 space-y-4">
          <p class="text-[11px] font-mono-tech uppercase tracking-widest text-teal-400 font-semibold">Begin with one conversation</p>
          <h2 class="text-3xl sm:text-4xl font-bold text-white tracking-tight">Give your work a second mind.</h2>
          <p class="text-xs sm:text-sm text-slate-400 max-w-md mx-auto">Your next meeting. Your next decision. The commitment you always have to search for.</p>
          <div class="pt-2">
            <button id="landing-cta-bottom" class="btn-mint-cta text-sm">
              <span>Start exploring free</span>
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
            </button>
          </div>
        </section>

        <!-- Footer -->
        <footer class="pt-8 pb-12 border-t border-white/5 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-4">
          <div class="flex items-center gap-2">
            <span class="text-teal-400 font-bold">Ω</span>
            <span>OMIMIND • Ambient Voice Intelligence</span>
          </div>
          <p>© 2026 OMIMIND • Mohammed Masood • HiDevs × Lyzr × Qdrant Hackathon</p>
        </footer>

      </div>
    </div>
  `;

  // Attach all handlers
  document.getElementById('landing-signin')?.addEventListener('click', openLoginModal);
  document.getElementById('landing-cta')?.addEventListener('click', openLoginModal);
  document.getElementById('landing-cta-hero')?.addEventListener('click', openLoginModal);
  document.getElementById('landing-cta-bottom')?.addEventListener('click', openLoginModal);
  document.getElementById('landing-try-ask')?.addEventListener('click', openLoginModal);
  document.getElementById('landing-learn')?.addEventListener('click', () => {
    document.getElementById('landing-how')?.scrollIntoView({ behavior: 'smooth' });
  });
}

export function openLoginModal() {
  openModal({
    title: 'Enter your OMIMIND workspace',
    subtitle: 'Sign in to access your ambient memories, meeting transcripts, and action drafts.',
    contentHtml: `
      <div class="space-y-5">
        <div class="flex items-center gap-4 p-3 rounded-xl bg-slate-900/80 border border-white/5">
          <div class="orb-container w-12 h-12 flex-shrink-0">
            <div class="orb-sphere"></div>
            <div class="orb-glow"></div>
          </div>
          <div class="text-xs space-y-0.5">
            <strong class="text-white block">Ambient Memory Layer</strong>
            <p class="text-slate-400 text-[11px]">Vector memory grounded in Qdrant with Lyzr Agent Studio swarms.</p>
          </div>
        </div>

        <div class="space-y-3">
          <div>
            <label for="input-auth-email" class="block text-xs font-semibold text-slate-300 mb-1.5">Email</label>
            <input 
              id="input-auth-email" 
              type="email" 
              placeholder="you@example.com" 
              autocomplete="email" 
              class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-white/10 text-white text-sm focus:outline-none focus:border-teal-500/50" 
            />
          </div>
          <div>
            <label for="input-auth-password" class="block text-xs font-semibold text-slate-300 mb-1.5">Password</label>
            <input 
              id="input-auth-password" 
              type="password" 
              placeholder="At least 8 characters" 
              autocomplete="current-password" 
              class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-white/10 text-white text-sm focus:outline-none focus:border-teal-500/50" 
            />
          </div>
          <div class="flex items-center justify-between text-xs pt-1">
            <button id="btn-auth-mode" class="text-teal-300 hover:text-teal-200 font-medium">Create an account</button>
            <button id="btn-auth-reset" class="text-slate-400 hover:text-white">Forgot password?</button>
          </div>
        </div>
      </div>
    `,
    actionsHtml: `
      <button id="btn-cancel-login" class="px-3.5 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white transition">Cancel</button>
      <button id="btn-submit-login" class="btn-mint-cta text-xs py-2 px-4">
        <span id="btn-submit-login-text">Sign In</span>
      </button>
    `,
  });

  const submitBtn = document.getElementById('btn-submit-login');
  const inputEl = document.getElementById('input-auth-password');
  const emailEl = document.getElementById('input-auth-email');
  const cancelBtn = document.getElementById('btn-cancel-login');
  const modeBtn = document.getElementById('btn-auth-mode');
  let signupMode = false;

  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  modeBtn?.addEventListener('click', () => { 
    signupMode = !signupMode; 
    modeBtn.innerText = signupMode ? 'Already have an account? Sign in' : 'Create an account'; 
    const labelSpan = document.getElementById('btn-submit-login-text');
    if (labelSpan) labelSpan.innerText = signupMode ? 'Create account' : 'Sign In'; 
  });

  const doLogin = async () => {
    const email = emailEl?.value?.trim();
    const password = inputEl?.value || '';
    if (!email || !password) {
      showToast('Enter an email and password.', 'warning');
      return;
    }
    submitBtn.disabled = true;
    const labelSpan = document.getElementById('btn-submit-login-text');
    if (labelSpan) labelSpan.innerText = 'Authenticating...';
    try {
      if (signupMode) {
        const result = await signUp(email, password);
        if (!result.session) {
          showToast('Account created. Check your inbox and verify your email before signing in.', 'success');
          submitBtn.disabled = false;
          if (labelSpan) labelSpan.innerText = 'Create account';
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
      if (labelSpan) labelSpan.innerText = signupMode ? 'Create account' : 'Sign In';
    }
  };

  if (submitBtn) submitBtn.addEventListener('click', doLogin);
  if (inputEl) {
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') doLogin();
    });
  }
  document.getElementById('btn-auth-reset')?.addEventListener('click', async () => { 
    const email = emailEl?.value?.trim(); 
    if (!email) return showToast('Enter your email first.', 'warning'); 
    try { 
      await resetPassword(email); 
      showToast('Password reset email sent.', 'success'); 
    } catch (err) { 
      showToast(err.message, 'error'); 
    } 
  });
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
