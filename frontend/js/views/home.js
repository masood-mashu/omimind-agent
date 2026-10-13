/**
 * home.js - Command Center View
 * Hero search, live Omi memory sync status, recent memories, meetings & actions.
 */

import { getState } from '../state.js';
import * as api from '../api.js';
import { navigate } from '../router.js';
import { showToast } from '../components/toast.js';

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[c]);
}

export function renderHome(container) {
  const state = getState();
  const qdrantPoints = state.health?.qdrant_stats?.points_count ?? 'Not loaded';
  const persistenceMode = state.health?.qdrant_persistence_mode ?? 'Configured storage';

  container.innerHTML = `
    <div class="view-container max-w-6xl mx-auto space-y-8 py-4 px-4 sm:px-6">
      
      <!-- Central Ingestion Hub: What do you want OMIMIND to remember? (Inspired by OmniMind Dashboard) -->
      <section class="omi-card p-6 border border-white/10 shadow-2xl relative overflow-hidden bg-gradient-to-b from-[#0f1523] to-[#090d14]">
        <div class="absolute -right-20 -top-20 w-72 h-72 bg-teal-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div class="absolute -left-20 -bottom-20 w-72 h-72 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 pb-6 border-b border-white/5 relative z-10">
          <div class="flex items-center gap-4">
            <div class="orb-container flex-shrink-0">
              <div class="orb-sphere"></div>
              <div class="orb-glow"></div>
            </div>
            <div class="space-y-1">
              <div class="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-teal-500/10 border border-teal-500/20 text-teal-300 text-[10px] font-mono-tech">
                <span class="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse"></span>
                <span>AMBIENT INTELLIGENCE HUB</span>
              </div>
              <h1 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                What do you want me to remember?
              </h1>
              <p class="text-xs sm:text-sm text-slate-400 max-w-xl">
                Speak it, type it, or process a meeting transcript. OMIMIND vectors, reasons, and dispatches.
              </p>
            </div>
          </div>

          <!-- Multi-Modal Action Toolbar -->
          <div class="flex items-center gap-2 sm:gap-2.5 flex-wrap flex-shrink-0">
            <button id="btn-home-mic" type="button" class="btn-mint-cta text-xs touch-target-44 shadow-lg shadow-teal-500/20">
              <svg class="w-4 h-4 text-teal-950" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z"/></svg>
              <span id="home-mic-text">Record voice note</span>
            </button>
            <button id="btn-home-type" type="button" class="touch-target-44 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-xs font-semibold text-slate-300 hover:text-white border border-white/10 flex items-center gap-2 transition" title="Type notes directly">
              <svg class="w-3.5 h-3.5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
              <span>Type note</span>
            </button>
            <a href="#meetings" class="touch-target-44 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-xs font-semibold text-slate-300 hover:text-white border border-white/10 flex items-center gap-2 transition" title="Choose a sample meeting">
              <svg class="w-3.5 h-3.5 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
              <span>Sample meetings</span>
            </a>
            <button id="btn-quick-sync" type="button" class="touch-target-44 px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white border border-white/10 text-xs font-medium transition" title="Sync memory points">
              Refresh
            </button>
          </div>
        </div>

        <!-- Direct Ingest Box & Category Tagging -->
        <div class="mt-5 space-y-3 relative z-10">
          <form id="home-inline-ingest-form" class="space-y-3">
            <div class="relative bg-slate-950/80 border border-white/10 rounded-2xl p-2.5 focus-within:border-teal-500/50 transition shadow-inner">
              <textarea 
                id="home-inline-type-input" 
                rows="2" 
                placeholder="Remember that... (e.g. Approved $120k cloud budget for Project Horizon, Sarah leading API v2 migration by Thursday)..." 
                class="w-full bg-transparent border-none p-2 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none resize-none font-sans"
              ></textarea>
              
              <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2 pt-2 border-t border-white/5 text-xs">
                <div class="flex items-center gap-2 text-slate-400 font-mono-tech text-[11px]">
                  <span>Category:</span>
                  <span class="px-2 py-0.5 rounded bg-white/5 text-teal-300 border border-white/5">Engineering</span>
                  <span class="text-slate-600">•</span>
                  <span class="text-slate-500">Vectorized with the configured provider into Qdrant</span>
                </div>
                
                <button 
                  type="submit" 
                  id="btn-home-inline-submit"
                  class="touch-target-44 px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs shadow-md transition flex items-center justify-center gap-1.5 flex-shrink-0"
                >
                  <span>Index Note</span>
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
                </button>
              </div>
            </div>
          </form>

          <p class="text-[10px] text-slate-500 font-mono-tech">
            384d dense vectors • Qdrant collection: <code class="text-teal-400">omi_ambient_memory</code> • Lyzr Studio swarm reasoning.
          </p>
        </div>

        <!-- Waveform Canvas -->
        <div class="mt-4 pt-3 border-t border-white/5">
          <canvas id="ambient-waveform" width="800" height="32" class="w-full h-8 rounded-lg"></canvas>
          <div class="flex items-center justify-between text-[10px] text-slate-500 mt-1">
            <span>Waveform shows live audio while mic recording; decorative while idle.</span>
            <span class="font-mono-tech text-teal-400">${qdrantPoints} vectors in storage</span>
          </div>
        </div>

      </section>

      <!-- Command Ask Bar Surface -->
      <section class="max-w-3xl mx-auto space-y-3">
        <form id="home-ask-form" class="relative group">
          <div class="absolute -inset-0.5 bg-gradient-to-r from-teal-500 to-indigo-600 rounded-2xl blur opacity-20 group-hover:opacity-35 transition"></div>
          <div class="relative flex items-center bg-[#0f1523] border border-white/10 rounded-2xl p-2 shadow-xl">
            <div class="pl-3.5 text-teal-400 flex items-center">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            </div>
            <input 
              id="home-ask-input" 
              type="text" 
              placeholder="Ask anything you've heard... (e.g. What budget was approved for Project Horizon?)"
              autocomplete="off"
              class="w-full bg-transparent border-none py-2.5 px-3 text-xs sm:text-sm text-white placeholder-slate-400 focus:outline-none"
            />
            <div class="hidden sm:flex items-center mr-2 px-2 py-1 rounded bg-slate-800 text-[10px] font-mono-tech text-slate-400">
              <span>⌘K</span>
            </div>
            <button 
              type="submit" 
              class="touch-target-44 px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs shadow-md transition flex items-center gap-1.5 flex-shrink-0"
            >
              <span>Ask OMIMIND</span>
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
            </button>
          </div>
        </form>

        <!-- Prompt Pills -->
        <div class="flex flex-wrap items-center justify-center gap-2 text-xs">
          <span class="text-slate-400 text-[11px] font-medium mr-1">Sample prompts:</span>
          <button type="button" class="home-pill query-pill cursor-pointer" data-query="What budget was approved for Project Horizon?">
            "What budget was approved for Project Horizon?"
          </button>
          <button type="button" class="home-pill query-pill cursor-pointer" data-query="What did Sarah say about the budget?">
            "What did Sarah say about the budget?"
          </button>
          <button type="button" class="home-pill query-pill cursor-pointer" data-query="What actions do I need to follow up on?">
            "What actions do I need to follow up on?"
          </button>
        </div>
      </section>

      <!-- 3 Telemetry Stat Cards -->
      <section class="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
        <div class="p-4 rounded-2xl bg-[#0f1523] border border-white/5 flex items-center justify-between">
          <div>
            <span class="text-[10px] font-mono-tech uppercase tracking-wider text-slate-400">Vector Points</span>
            <div class="text-2xl font-bold text-white mt-0.5">${qdrantPoints}</div>
            <span class="text-[10px] text-teal-400 font-mono-tech">Qdrant Cloud (${persistenceMode})</span>
          </div>
          <div class="w-10 h-10 rounded-xl bg-teal-500/10 flex items-center justify-center text-teal-400 text-lg">
            🧠
          </div>
        </div>

        <div class="p-4 rounded-2xl bg-[#0f1523] border border-white/5 flex items-center justify-between">
          <div>
            <span class="text-[10px] font-mono-tech uppercase tracking-wider text-slate-400">Extracted Actions</span>
            <div class="text-2xl font-bold text-white mt-0.5">${state.actions?.length || 0}</div>
            <span class="text-[10px] text-amber-300 font-mono-tech">Commitments tracked</span>
          </div>
          <div class="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-400 text-lg">
            ⚡
          </div>
        </div>

        <div class="p-4 rounded-2xl bg-[#0f1523] border border-white/5 flex items-center justify-between">
          <div>
            <span class="text-[10px] font-mono-tech uppercase tracking-wider text-slate-400">Meetings Analyzed</span>
            <div class="text-2xl font-bold text-white mt-0.5">${state.meetings?.length || 0}</div>
            <span class="text-[10px] text-indigo-300 font-mono-tech">Lyzr swarm synthesized</span>
          </div>
          <div class="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center text-indigo-400 text-lg">
            📅
          </div>
        </div>
      </section>

      <!-- "Needs your attention" Review Section (Pattern from OmniMind Inspection) -->
      <section class="attention-review-box p-5 space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <svg class="w-4 h-4 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>
            <h2 class="text-xs sm:text-sm font-bold text-white tracking-wide">Needs your review</h2>
          </div>
          <span class="px-2 py-0.5 rounded text-[10px] font-mono-tech bg-amber-500/20 text-amber-300 border border-amber-500/30">
            AI suggestions need confirmation
          </span>
        </div>
        <p class="text-xs text-slate-300">
          Suggestions extracted from your spoken conversations. Review the assignees, deadlines, and details before dispatching to Jira or Google Calendar.
        </p>
        <div class="flex items-center justify-between pt-1 text-xs">
          <div class="flex items-center gap-2">
            <span class="text-slate-400 font-mono-tech text-[11px]">High priority commitments:</span>
            <span class="text-teal-300 font-semibold">${state.actions?.length ? state.actions.length + ' pending' : '0 pending'}</span>
          </div>
          <a href="#actions" class="text-teal-400 hover:text-teal-300 font-medium flex items-center gap-1">
            <span>Open Action Center</span>
            <span aria-hidden="true">→</span>
          </a>
        </div>
      </section>

      <!-- Multi-Column Activity Grid -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">

        <!-- Column 1: Recent Memories -->
        <div class="omi-card p-5 space-y-4 flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between border-b border-white/5 pb-3">
              <div class="flex items-center gap-2">
                <span class="text-teal-400 font-bold">🧠</span>
                <h2 class="font-bold text-sm text-white">Recent Ambient Memories</h2>
              </div>
              <a href="#memory" class="text-xs text-teal-400 hover:underline">View All →</a>
            </div>
            <div id="home-memories-list" class="space-y-3 mt-3.5">
              ${renderMemoriesPreview(state.memories)}
            </div>
          </div>
          <a href="#memory" class="w-full py-2.5 rounded-xl border border-white/10 hover:border-teal-500/30 text-xs text-slate-200 font-medium transition text-center block mt-3 bg-slate-900/60 hover:bg-slate-800/80">
            Open Memory Explorer
          </a>
        </div>

        <!-- Column 2: Recent Meetings -->
        <div class="omi-card p-5 space-y-4 flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between border-b border-white/5 pb-3">
              <div class="flex items-center gap-2">
                <span class="text-indigo-400 font-bold">📅</span>
                <h2 class="font-bold text-sm text-white">Recent Meetings</h2>
              </div>
              <a href="#meetings" class="text-xs text-indigo-400 hover:underline">View All →</a>
            </div>
            <div id="home-meetings-list" class="space-y-3 mt-3.5">
              ${renderMeetingsPreview(state.meetings)}
            </div>
          </div>
          <a href="#meetings" class="w-full py-2.5 rounded-xl border border-white/10 hover:border-indigo-500/30 text-xs text-slate-200 font-medium transition text-center block mt-3 bg-slate-900/60 hover:bg-slate-800/80">
            Open Meeting Intelligence
          </a>
        </div>

        <!-- Column 3: Important Actions -->
        <div class="omi-card p-5 space-y-4 flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between border-b border-white/5 pb-3">
              <div class="flex items-center gap-2">
                <span class="text-amber-400 font-bold">⚡</span>
                <h2 class="font-bold text-sm text-white">Extracted Action Items</h2>
              </div>
              <a href="#actions" class="text-xs text-amber-400 hover:underline">View All →</a>
            </div>
            <div id="home-actions-list" class="space-y-3 mt-3.5">
              ${renderActionsPreview(state.actions)}
            </div>
          </div>
          <a href="#actions" class="w-full py-2.5 rounded-xl border border-white/10 hover:border-amber-500/30 text-xs text-slate-200 font-medium transition text-center block mt-3 bg-slate-900/60 hover:bg-slate-800/80">
            Open Action Center
          </a>
        </div>

      </div>

      <!-- Pipeline Overview: How meeting processing works -->
      <section class="omi-card p-5 border border-white/10 shadow-xl relative overflow-hidden">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-white/5 gap-2 relative z-10">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-teal-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-teal-500/20">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h2 class="text-sm font-bold text-white tracking-wide">Multi-Agent Processing Pipeline</h2>
                <span class="px-2 py-0.5 rounded text-[10px] font-mono-tech bg-teal-500/10 text-teal-300 border border-teal-500/20">
                  Lyzr Swarm + Qdrant
                </span>
              </div>
              <p class="text-[11px] text-slate-400 font-mono-tech mt-0.5">End-to-end trace from ambient voice capture to deterministic dispatch.</p>
            </div>
          </div>
          <a href="#activity" class="text-xs text-teal-400 hover:text-teal-300 font-medium px-2 py-1 rounded hover:bg-white/5 transition">
            Live Feed →
          </a>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 mt-4 relative z-10">
          <div class="p-3.5 rounded-xl bg-slate-900/80 border border-teal-500/30">
            <div class="flex items-center justify-between mb-2">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono-tech bg-teal-500/20 text-teal-300 font-bold">01 // MEMORY AGENT</span>
              <span class="text-[10px] font-mono-tech text-emerald-400 font-semibold">Live</span>
            </div>
            <h3 class="text-xs font-bold text-white">Qdrant Vector Retrieval</h3>
            <p class="text-[11px] text-slate-400 mt-1 font-mono-tech">Embeds speech & queries <code class="text-teal-300">omi_ambient_memory</code> with 384d cosine similarity.</p>
          </div>

          <div class="p-3.5 rounded-xl bg-slate-900/80 border border-indigo-500/30">
            <div class="flex items-center justify-between mb-2">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono-tech bg-indigo-500/20 text-indigo-300 font-bold">02 // REASONER AGENT</span>
              <span class="text-[10px] font-mono-tech text-indigo-300 font-semibold">Active</span>
            </div>
            <h3 class="text-xs font-bold text-white">Contextual Synthesis</h3>
            <p class="text-[11px] text-slate-400 mt-1 font-mono-tech">Lyzr manager agent cross-references past meetings, speakers, and budget context.</p>
          </div>

          <div class="p-3.5 rounded-xl bg-slate-900/80 border border-amber-500/30">
            <div class="flex items-center justify-between mb-2">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono-tech bg-amber-500/20 text-amber-300 font-bold">03 // ACTION EXTRACTOR</span>
              <span class="text-[10px] font-mono-tech text-amber-300 font-semibold">Review</span>
            </div>
            <h3 class="text-xs font-bold text-white">Commitment Ledger</h3>
            <p class="text-[11px] text-slate-400 mt-1 font-mono-tech">Parses spoken promises into structured assignees, deadlines, and priority tags.</p>
          </div>

          <div class="p-3.5 rounded-xl bg-slate-900/80 border border-purple-500/30">
            <div class="flex items-center justify-between mb-2">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono-tech bg-purple-500/20 text-purple-300 font-bold">04 // TASK DISPATCHER</span>
              <span class="text-[10px] font-mono-tech text-purple-300 font-semibold">Dispatch</span>
            </div>
            <h3 class="text-xs font-bold text-white">Execution Gateway</h3>
            <p class="text-[11px] text-slate-400 mt-1 font-mono-tech">Generates follow-up email drafts, Jira ticket payloads, and calendar schedule events.</p>
          </div>
        </div>
      </section>

    </div>
  `;

  // Attach event handlers
  const askForm = container.querySelector('#home-ask-form');
  const askInput = container.querySelector('#home-ask-input');
  if (askForm && askInput) {
    askForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const q = askInput.value.trim();
      if (!q) return;
      navigate(`ask?q=${encodeURIComponent(q)}`);
    });
  }

  container.querySelectorAll('.home-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      const q = btn.getAttribute('data-query');
      if (q) navigate(`ask?q=${encodeURIComponent(q)}`);
    });
  });

  const syncBtn = container.querySelector('#btn-quick-sync');
  if (syncBtn) {
    syncBtn.addEventListener('click', async () => {
      syncBtn.disabled = true;
      syncBtn.innerText = 'Syncing...';
      try {
        const memData = await api.fetchMemories(30);
        state.memories = memData.memories || [];
        const health = await api.fetchHealth();
        state.health = health;
        renderHome(container);
        showToast('Memory synced with Qdrant Cloud');
      } catch (err) {
        showToast('Sync error: ' + err.message, 'warning');
      } finally {
        syncBtn.disabled = false;
        syncBtn.innerText = 'Refresh Memory';
      }
    });
  }

  const inlineForm = container.querySelector('#home-inline-ingest-form');
  const inlineInput = container.querySelector('#home-inline-type-input');
  const inlineSubmit = container.querySelector('#btn-home-inline-submit');
  if (inlineForm && inlineInput) {
    inlineForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const text = inlineInput.value.trim();
      if (!text) {
        showToast('Please enter note or memo text to vectorize.', 'warning');
        return;
      }
      if (inlineSubmit) {
        inlineSubmit.disabled = true;
        inlineSubmit.innerHTML = `
          <span class="w-3 h-3 rounded-full border-2 border-white/20 border-t-white animate-spin"></span>
          <span>Indexing...</span>
        `;
      }
      try {
        await api.streamPipeline('/api/custom-voice-stream', {
          transcript: text,
          speaker: 'User',
          title: 'Direct Quick Note'
        }, {
          onComplete: async (dossier) => {
            showToast('Note vectorized and indexed into Qdrant memory!');
            inlineInput.value = '';
            const memData = await api.fetchMemories(30);
            state.memories = memData.memories || [];
            const memoriesList = container.querySelector('#home-memories-list');
            if (memoriesList) {
              memoriesList.innerHTML = renderMemoriesPreview(state.memories);
            }
          },
          onError: (err) => {
            showToast('Indexing error: ' + (err.message || 'Failed'), 'warning');
          }
        });
      } catch (err) {
        showToast('Submission error: ' + err.message, 'warning');
      } finally {
        if (inlineSubmit) {
          inlineSubmit.disabled = false;
          inlineSubmit.innerHTML = `
            <span>Index Note</span>
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
          `;
        }
      }
    });
  }
}

function renderMemoriesPreview(memories) {
  if (!memories || memories.length === 0) {
    return `
      <div class="py-6 text-center text-slate-400 text-xs">
        <p>No ambient memories captured yet.</p>
        <p class="text-[11px] mt-1 text-slate-400">Speak into the mic or connect Omi to begin.</p>
      </div>
    `;
  }
  return memories.slice(0, 3).map(m => `
    <div class="p-3 rounded-xl bg-slate-900/60 border border-white/5 hover:border-white/10 transition text-xs space-y-1">
      <div class="flex items-center justify-between">
        <span class="font-semibold text-cyan-300 font-mono-tech text-[11px]">${escapeHtml(m.speaker || 'Omi User')}</span>
        <span class="text-slate-400 text-[10px] font-sans">${escapeHtml(m.timestamp_str || 'live')}</span>
      </div>
      <p class="text-slate-200 line-clamp-2 italic font-sans">"${escapeHtml(m.text)}"</p>
    </div>
  `).join('');
}

function renderMeetingsPreview(meetings) {
  if (!meetings || meetings.length === 0) {
    return `<div class="py-6 text-center text-slate-400 text-xs">No meetings loaded yet.</div>`;
  }
  return meetings.slice(0, 3).map(m => `
    <a href="#meeting/${escapeHtml(m.id)}" class="omi-card-interactive block p-3 rounded-xl bg-slate-900/60 border border-white/5 hover:border-white/15 transition text-xs space-y-1">
      <div class="flex items-center justify-between">
        <span class="font-semibold text-white text-xs truncate max-w-[70%]">${escapeHtml(m.title)}</span>
        <span class="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 font-mono-tech">${escapeHtml(m.duration || '')}</span>
      </div>
      <p class="text-slate-400 text-[11px] font-sans">${escapeHtml(m.category || 'Meeting')} • ${m.participants ? m.participants.length : 0} attendees</p>
    </a>
  `).join('');
}

function renderActionsPreview(actions) {
  if (!actions || actions.length === 0) {
    return `
      <div class="py-6 text-center text-slate-400 text-xs">
        <p>No action items extracted yet.</p>
        <p class="text-[11px] mt-1 text-slate-400">Process a meeting to extract commitments.</p>
      </div>
    `;
  }
  return actions.slice(0, 3).map(a => `
    <div class="p-3 rounded-xl bg-slate-900/60 border border-white/5 hover:border-white/10 transition text-xs space-y-1">
      <div class="flex items-center justify-between">
        <span class="font-semibold text-white truncate max-w-[70%] font-sans">${escapeHtml(a.title)}</span>
        <span class="px-1.5 py-0.5 rounded text-[10px] font-mono-tech ${
          a.priority === 'Critical' ? 'bg-rose-500/20 text-rose-300' :
          a.priority === 'High' ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-800 text-slate-300'
        }">${escapeHtml(a.priority || 'Normal')}</span>
      </div>
      <p class="text-slate-400 text-[11px] font-sans">Assigned to: <span class="text-cyan-300 font-semibold">${escapeHtml(a.assignee || 'Team')}</span> • Due ${escapeHtml(a.due_date || 'Upcoming')}</p>
    </div>
  `).join('');
}
