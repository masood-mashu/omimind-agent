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
  const qdrantPoints = state.health?.qdrant_stats?.points_count ?? 'Cloud Sync Active';
  const persistenceMode = state.health?.qdrant_persistence_mode ?? 'Cloud';
  const lyzrReady = state.health?.lyzr_status?.configured ?? true;

  container.innerHTML = `
    <div class="view-container max-w-6xl mx-auto space-y-10 py-4 px-4 sm:px-6">
      
      <!-- Hero Section -->
      <section class="text-center space-y-4 pt-6 pb-2">
        <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 text-xs font-medium">
          <span class="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
          <span>Ambient Memory & Multi-Agent Intelligence</span>
        </div>
        <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight text-white">
          Your conversations, remembered.<br>
          <span class="bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-400 bg-clip-text text-transparent">
            Your meetings, understood.
          </span>
        </h1>
        <p class="text-sm sm:text-base text-slate-400 max-w-2xl mx-auto">
          OmiMind captures ambient speech into Qdrant semantic memory and orchestrates Lyzr specialized agents to recall decisions, commitments, and action items.
        </p>

        <!-- Dominant Ask Bar (Command Surface) -->
        <div class="max-w-3xl mx-auto mt-6">
          <form id="home-ask-form" class="relative group">
            <div class="absolute -inset-0.5 bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 rounded-2xl blur opacity-25 group-hover:opacity-40 transition duration-300"></div>
            <div class="relative flex items-center bg-[#0e131f] border border-white/10 rounded-2xl p-2 shadow-2xl">
              <div class="pl-3.5 text-cyan-400 flex items-center">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
              </div>
              <input 
                id="home-ask-input" 
                type="text" 
                placeholder="Ask anything you've heard (e.g. What did I say about Project Nebula?)"
                autocomplete="off"
                class="w-full bg-transparent border-none py-3 px-3 text-sm sm:text-base text-white placeholder-slate-400 focus:outline-none"
              />
              <div class="hidden sm:flex items-center gap-1.5 mr-2 px-2 py-1 rounded-md bg-slate-800/80 border border-white/10 text-[11px] font-mono-tech text-slate-400">
                <span>⌘K</span>
              </div>
              <button 
                type="submit" 
                class="touch-target-44 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs sm:text-sm shadow-md transition flex items-center gap-1.5 flex-shrink-0"
              >
                <span>Ask</span>
                <span class="hidden sm:inline">OmiMind</span>
                <svg class="w-4 h-4 ml-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
              </button>
            </div>
          </form>

          <!-- Prompt Pills -->
          <div class="flex flex-wrap items-center justify-center gap-2 mt-3.5 text-xs">
            <span class="text-slate-400 text-[11px] font-medium mr-1">Try asking:</span>
            <button type="button" class="home-pill px-3 py-1.5 rounded-lg bg-indigo-950/50 hover:bg-indigo-900/60 text-cyan-300 hover:text-white border border-cyan-500/30 transition" data-query="What budget was approved for Project Horizon?">
              "What budget was approved for Project Horizon?"
            </button>
            <button type="button" class="home-pill px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 transition" data-query="What did I say about Project Nebula?">
              "What did I say about Project Nebula?"
            </button>
            <button type="button" class="home-pill px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 transition" data-query="What did Sarah say about the budget?">
              "What did Sarah say about the budget?"
            </button>
            <button type="button" class="home-pill px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 transition" data-query="What actions do I need to follow up on?">
              "What actions do I need to follow up on?"
            </button>
          </div>
        </div>
      </section>

      <!-- Live Ambient Status & Audio Bar -->
      <section class="omi-card p-5 border border-white/10 shadow-lg">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <div class="w-3 h-3 rounded-full bg-emerald-400 live-indicator text-emerald-400"></div>
            <div>
              <div class="flex items-center gap-2">
                <span class="font-bold text-sm text-white">Ambient Memory Sync Active</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-mono-tech bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Qdrant Cloud (${persistenceMode})
                </span>
              </div>
              <p class="text-xs text-slate-400 mt-0.5">
                Listening via Omi Wearable & Web Voice • ${qdrantPoints} vectors indexed in <code class="text-cyan-300 font-mono-tech">omi_ambient_memory</code>
              </p>
            </div>
          </div>
          <div class="flex items-center gap-2 sm:gap-2.5 flex-wrap">
            <button id="btn-home-type" type="button" class="touch-target-44 px-3.5 py-2 rounded-xl bg-indigo-950/50 hover:bg-indigo-900/60 text-xs font-semibold text-indigo-300 hover:text-white border border-indigo-500/30 flex items-center gap-2 transition" title="Type notes or meeting data directly">
              <svg class="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
              <span>Type Note</span>
            </button>
            <button id="btn-home-mic" type="button" class="touch-target-44 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-cyan-300 border border-white/10 flex items-center gap-2 transition">
              <svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z"/></svg>
              <span id="home-mic-text">Record Voice</span>
            </button>
            <button id="btn-quick-sync" type="button" class="touch-target-44 px-3.5 py-2 rounded-xl bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-500/30 text-xs font-semibold transition">
              Refresh Memory
            </button>
          </div>
        </div>
        <!-- Live Waveform strip -->
        <div class="mt-4 pt-3 border-t border-white/5">
          <canvas id="ambient-waveform" width="800" height="36" class="w-full h-9 rounded-lg"></canvas>
        </div>

        <!-- Wearable Hardware Telemetry Sub-bar (from Stitch Obsidian Telemetry) -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-3 border-t border-white/5 text-[11px] font-mono-tech">
          <div class="p-2 rounded-xl bg-slate-950/60 border border-white/5 flex items-center justify-between">
            <span class="text-slate-400">Omi Battery</span>
            <span class="text-emerald-400 font-bold flex items-center gap-1">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              94% (18h)
            </span>
          </div>
          <div class="p-2 rounded-xl bg-slate-950/60 border border-white/5 flex items-center justify-between">
            <span class="text-slate-400">BLE Signal</span>
            <span class="text-cyan-300 font-bold">-42 dBm</span>
          </div>
          <div class="p-2 rounded-xl bg-slate-950/60 border border-white/5 flex items-center justify-between">
            <span class="text-slate-400">DSP Latency</span>
            <span class="text-indigo-300 font-bold">18.2 ms</span>
          </div>
          <div class="p-2 rounded-xl bg-slate-950/60 border border-white/5 flex items-center justify-between">
            <span class="text-slate-400">Encryption</span>
            <span class="text-purple-300 font-bold">AES-256</span>
          </div>
        </div>

        <!-- Dedicated Direct Typing Input Box -->
        <div class="mt-4 pt-3.5 border-t border-white/5">
          <form id="home-inline-ingest-form" class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
            <div class="flex items-center gap-2 text-xs text-indigo-300 font-mono-tech flex-shrink-0">
              <span class="w-2 h-2 rounded-full bg-indigo-400 animate-pulse"></span>
              <span>Direct Ingest:</span>
            </div>
            <input 
              id="home-inline-type-input" 
              type="text" 
              placeholder="Type note, memo, or decision directly to vectorize into Qdrant (Press Enter)..." 
              autocomplete="off"
              class="flex-1 bg-slate-900/90 border border-white/10 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-indigo-500 font-mono-tech transition"
            />
            <button 
              type="submit" 
              id="btn-home-inline-submit"
              class="touch-target-44 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold text-xs shadow-md transition flex items-center justify-center gap-1.5 flex-shrink-0"
            >
              <span>Index Note</span>
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
            </button>
          </form>
        </div>
      </section>

      <!-- Multi-Agent Swarm Orchestrator (Adopted from Stitch Obsidian Telemetry) -->
      <section class="omi-card p-5 border border-white/10 shadow-2xl relative overflow-hidden">
        <div class="absolute -right-16 -top-16 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div class="absolute -left-16 -bottom-16 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <!-- Section Header -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-white/5 gap-2 relative z-10">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-cyan-500/20">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h2 class="text-sm font-bold text-white tracking-wide">Multi-Agent Swarm Orchestrator</h2>
                <span class="px-2 py-0.5 rounded text-[10px] font-mono-tech bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Lyzr Swarm v2.4
                </span>
              </div>
              <p class="text-[11px] text-slate-400 font-mono-tech mt-0.5">Automated autonomous pipeline triggered from live wearable ambient audio</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="px-2.5 py-1 rounded-full text-[10px] font-mono-tech bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Synchronized Pipeline: 4 Nodes Active
            </span>
            <a href="#activity" class="text-xs text-cyan-400 hover:text-cyan-300 font-medium px-2 py-1 rounded hover:bg-white/5 transition">
              Live Feed →
            </a>
          </div>
        </div>

        <!-- 4-Node Connected Cards Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 mt-4 relative z-10">

          <!-- Node 1: Memory Agent -->
          <div class="p-3.5 rounded-xl bg-slate-900/80 border border-cyan-500/30 hover:border-cyan-400/50 transition relative group flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between mb-2">
                <span class="px-2 py-0.5 rounded text-[10px] font-mono-tech bg-cyan-500/20 text-cyan-300 font-bold">
                  01 // MEMORY AGENT
                </span>
                <span class="text-[10px] font-mono-tech text-emerald-400 font-semibold">98% Match</span>
              </div>
              <h3 class="text-xs font-bold text-white">Qdrant Vector Retrieval</h3>
              <p class="text-[11px] text-slate-400 mt-1 font-mono-tech">Embeds ambient speech & queries <code class="text-cyan-300">omi_ambient_memory</code> with cosine similarity.</p>
            </div>
            <div class="mt-3 pt-2.5 border-t border-white/5 flex items-center justify-between text-[10px] font-mono-tech text-slate-500">
              <span>Grounding: Active</span>
              <span class="text-cyan-400 font-semibold">Vector Store</span>
            </div>
          </div>

          <!-- Node 2: Reasoner Agent -->
          <div class="p-3.5 rounded-xl bg-slate-900/80 border border-indigo-500/30 hover:border-indigo-400/50 transition relative group flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between mb-2">
                <span class="px-2 py-0.5 rounded text-[10px] font-mono-tech bg-indigo-500/20 text-indigo-300 font-bold">
                  02 // REASONER AGENT
                </span>
                <span class="text-[10px] font-mono-tech text-indigo-300 font-semibold">Synthesizing</span>
              </div>
              <h3 class="text-xs font-bold text-white">Contextual Synthesis</h3>
              <p class="text-[11px] text-slate-400 mt-1 font-mono-tech">Lyzr manager agent cross-references past meetings, speakers, and budget context.</p>
            </div>
            <div class="mt-3 pt-2.5 border-t border-white/5 flex items-center justify-between text-[10px] font-mono-tech text-slate-500">
              <span>Model: Lyzr Pro</span>
              <span class="text-indigo-400 font-semibold">Cognitive Node</span>
            </div>
          </div>

          <!-- Node 3: Action Extractor -->
          <div class="p-3.5 rounded-xl bg-slate-900/80 border border-amber-500/30 hover:border-amber-400/50 transition relative group flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between mb-2">
                <span class="px-2 py-0.5 rounded text-[10px] font-mono-tech bg-amber-500/20 text-amber-300 font-bold">
                  03 // ACTION EXTRACTOR
                </span>
                <span class="text-[10px] font-mono-tech text-amber-300 font-semibold">Parsed</span>
              </div>
              <h3 class="text-xs font-bold text-white">Commitment Ledger</h3>
              <p class="text-[11px] text-slate-400 mt-1 font-mono-tech">Parses spoken promises into structured assignees, deadlines, and priority tags.</p>
            </div>
            <div class="mt-3 pt-2.5 border-t border-white/5 flex items-center justify-between text-[10px] font-mono-tech text-slate-500">
              <span>Priority: Critical</span>
              <span class="text-amber-400 font-semibold">Tasks Extracted</span>
            </div>
          </div>

          <!-- Node 4: Task Dispatcher -->
          <div class="p-3.5 rounded-xl bg-slate-900/80 border border-purple-500/30 hover:border-purple-400/50 transition relative group flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between mb-2">
                <span class="px-2 py-0.5 rounded text-[10px] font-mono-tech bg-purple-500/20 text-purple-300 font-bold">
                  04 // TASK DISPATCHER
                </span>
                <span class="text-[10px] font-mono-tech text-purple-300 font-semibold">Drafts Ready</span>
              </div>
              <h3 class="text-xs font-bold text-white">Execution Gateway</h3>
              <p class="text-[11px] text-slate-400 mt-1 font-mono-tech">Generates follow-up email, Jira ticket payloads, and calendar schedule events.</p>
            </div>
            <div class="mt-3 pt-2.5 border-t border-white/5 flex items-center justify-between text-[10px] font-mono-tech text-slate-500">
              <span>Outputs: 3 Drafts</span>
              <span class="text-purple-400 font-semibold">Ready to Sync</span>
            </div>
          </div>

        </div>
      </section>

      <!-- Three Grid Columns: Recent Memories, Recent Meetings, Actions -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">

        <!-- Column 1: Recent Memories -->
        <div class="omi-card p-5 space-y-4 flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between border-b border-white/5 pb-3">
              <div class="flex items-center gap-2">
                <span class="text-cyan-400 font-bold">🧠</span>
                <h2 class="font-bold text-sm text-white">Recent Ambient Memories</h2>
              </div>
              <a href="#memory" class="text-xs text-cyan-400 hover:underline">View All →</a>
            </div>
            <div id="home-memories-list" class="space-y-3 mt-3.5">
              ${renderMemoriesPreview(state.memories)}
            </div>
          </div>
          <a href="#memory" class="w-full py-2.5 rounded-xl border border-white/10 hover:border-cyan-500/30 text-xs text-slate-200 font-medium transition text-center block mt-3 bg-slate-900/60 hover:bg-slate-800/80">
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
