/**
 * memory.js - Dedicated Second Brain Memory View
 * Semantic search over ambient conversational memory, speaker attribution, and privacy control.
 */

import { getState } from '../state.js';
import * as api from '../api.js';
import { showToast } from '../components/toast.js';

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[c]);
}

export async function renderMemory(container) {
  const state = getState();

  container.innerHTML = `
    <div class="view-container max-w-5xl mx-auto space-y-6 py-4 px-4 sm:px-6">
      
      <!-- Top Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-4">
        <div>
          <h1 class="text-xl sm:text-2xl font-bold text-white flex items-center gap-2.5">
            <span class="text-cyan-400">🧠</span>
            <span>Ambient Memory</span>
          </h1>
          <p class="text-xs sm:text-sm text-slate-400 mt-0.5">
            Your personal second brain. Automatically indexed conversations, meetings, and voice memos.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <span class="px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 text-xs font-mono-tech">
            Qdrant Cloud · 384-dim Vectors
          </span>
        </div>
      </div>

      <!-- Semantic Search Bar & Horizontal Topic Filter Rail -->
      <div class="omi-card p-4 space-y-3 border border-white/10 bg-[#0e131f]">
        <form id="memory-search-form" class="relative">
          <div class="flex items-center bg-slate-900/90 border border-white/10 rounded-xl px-3 py-1.5 focus-within:border-cyan-500/50 transition">
            <svg class="w-4 h-4 text-cyan-400 mr-2.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            <input 
              id="memory-search-input" 
              type="text" 
              placeholder="Search your conversations semantically (e.g. Project Nebula, GPU cluster, security)..."
              class="w-full bg-transparent border-none py-2 text-xs sm:text-sm text-white placeholder-slate-400 focus:outline-none"
            />
            <button type="submit" class="touch-target-44 px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs transition ml-2 flex-shrink-0">
              Search
            </button>
          </div>
        </form>

        <!-- Horizontal Filter Rail (Single-line, non-wrapping on mobile) -->
        <div class="omi-filter-rail items-center pt-1" aria-label="Quick topic filters">
          <span class="text-slate-400 text-[11px] font-medium flex-shrink-0 mr-1">Topics:</span>
          <button type="button" class="memory-topic-chip touch-target-44 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 text-xs whitespace-nowrap transition" data-topic="">
            All Topics
          </button>
          <button type="button" class="memory-topic-chip touch-target-44 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 text-xs whitespace-nowrap transition" data-topic="Project Nebula">
            Project Nebula
          </button>
          <button type="button" class="memory-topic-chip touch-target-44 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 text-xs whitespace-nowrap transition" data-topic="GPU">
            GPU Cluster
          </button>
          <button type="button" class="memory-topic-chip touch-target-44 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 text-xs whitespace-nowrap transition" data-topic="Security">
            Security & Auth
          </button>
          <button type="button" class="memory-topic-chip touch-target-44 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 text-xs whitespace-nowrap transition" data-topic="Budget">
            Budget
          </button>
        </div>

        <div id="memory-search-feedback" class="hidden text-xs text-cyan-300 font-mono-tech flex items-center justify-between px-1">
          <span id="memory-search-count">0 memories found</span>
          <button id="memory-clear-search" class="touch-target-44 text-slate-400 hover:text-white underline text-[11px]">Clear search</button>
        </div>
      </div>

      <!-- Memories List Container -->
      <div id="memories-container" class="space-y-3 min-h-[300px]">
        <div class="p-8 text-center text-slate-300 text-xs">
          <span class="w-2.5 h-2.5 rounded-full bg-cyan-400 inline-block animate-ping mr-2"></span>
          Retrieving ambient memories...
        </div>
      </div>

    </div>
  `;

  const searchForm = container.querySelector('#memory-search-form');
  const searchInput = container.querySelector('#memory-search-input');
  const feedbackDiv = container.querySelector('#memory-search-feedback');
  const countSpan = container.querySelector('#memory-search-count');
  const clearBtn = container.querySelector('#memory-clear-search');
  const memoriesList = container.querySelector('#memories-container');

  async function loadAllMemories() {
    try {
      const data = await api.fetchMemories(40);
      state.memories = data.memories || [];
      renderMemoryCards(memoriesList, state.memories);
      if (feedbackDiv) feedbackDiv.classList.add('hidden');
    } catch (err) {
      if (memoriesList) {
        memoriesList.innerHTML = `
          <div class="omi-card p-8 text-center text-slate-400 text-xs space-y-2">
            <p class="text-white font-medium">Unable to load memories</p>
            <p>${escapeHtml(err.message)}</p>
          </div>
        `;
      }
    }
  }

  async function performSemanticSearch(query) {
    if (!query || !query.trim()) {
      return loadAllMemories();
    }
    const cleanQ = query.trim();
    if (memoriesList) {
      memoriesList.innerHTML = `
        <div class="p-8 text-center text-slate-400 text-xs">
          <span class="w-2.5 h-2.5 rounded-full bg-cyan-400 inline-block animate-ping mr-2"></span>
          Searching Qdrant memory for "${escapeHtml(cleanQ)}"...
        </div>
      `;
    }

    try {
      const res = await api.queryMemory(cleanQ, 10);
      const matches = res.matches || [];
      if (feedbackDiv && countSpan) {
        feedbackDiv.classList.remove('hidden');
        countSpan.innerText = `${matches.length} semantic matches · Top relevance: ${Number(res.relevance_top || 0).toFixed(2)}`;
      }
      renderMemoryCards(memoriesList, matches, true);
    } catch (err) {
      showToast('Search failed: ' + err.message, 'warning');
      loadAllMemories();
    }
  }

  if (searchForm && searchInput) {
    searchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      performSemanticSearch(searchInput.value);
    });

    let debounceTimer;
    searchInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        if (!searchInput.value.trim()) {
          loadAllMemories();
        } else {
          performSemanticSearch(searchInput.value);
        }
      }, 400);
    });
  }

  if (clearBtn && searchInput) {
    clearBtn.addEventListener('click', () => {
      searchInput.value = '';
      loadAllMemories();
    });
  }

  // Topic filter chip clicks
  container.querySelectorAll('.memory-topic-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      const topic = btn.getAttribute('data-topic');
      if (searchInput) searchInput.value = topic;
      performSemanticSearch(topic);
    });
  });

  // Initial load
  loadAllMemories();
}

function renderMemoryCards(container, list, isSearchResults = false) {
  if (!list || list.length === 0) {
    container.innerHTML = `
      <div class="omi-card p-12 text-center text-slate-300 space-y-2">
        <p class="font-medium text-white">No memories found</p>
        <p class="text-xs text-slate-400">Ambient conversations captured by Omi will be preserved here.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = list.map(m => `
    <div class="omi-card p-4 space-y-2.5 border border-white/5 hover:border-white/10 transition">
      <div class="flex items-center justify-between text-xs">
        <div class="flex items-center gap-2">
          <span class="font-bold text-cyan-300 font-mono-tech text-xs">${escapeHtml(m.speaker || 'Omi User')}</span>
          ${m.timestamp_str ? `<span class="text-slate-400 font-mono-tech text-[10px]">@ ${escapeHtml(m.timestamp_str)}</span>` : ''}
          ${m.topic && m.topic !== 'general' ? `<span class="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 font-mono-tech">${escapeHtml(m.topic)}</span>` : ''}
        </div>
        <div class="flex items-center gap-2">
          ${m.score !== undefined ? `
            <span class="px-2 py-0.5 rounded text-[10px] font-mono-tech bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
              Relevance: ${Number(m.score).toFixed(2)}
            </span>
          ` : ''}
          <button data-delete-id="${escapeHtml(m.id || '')}" data-session-id="${escapeHtml(m.session_id || '')}" class="btn-forget-memory touch-target-44 text-slate-400 hover:text-rose-400 transition" title="Purge this memory for privacy" aria-label="Purge memory">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
          </button>
        </div>
      </div>

      <p class="text-slate-100 text-xs sm:text-sm font-sans leading-relaxed">
        "${escapeHtml(m.text)}"
      </p>

      <!-- Expandable Technical Details (Clean product UX by default) -->
      <details class="text-[11px] text-slate-400 pt-1 border-t border-white/5">
        <summary class="cursor-pointer text-slate-400 hover:text-slate-300 font-mono-tech text-[10px] select-none py-1">
          Technical Metadata
        </summary>
        <div class="mt-2 p-2.5 rounded-lg bg-slate-950 font-mono-tech text-[10px] space-y-1 text-slate-400 border border-white/5">
          ${m.id ? `<div>Point ID: <span class="text-slate-300">${escapeHtml(m.id)}</span></div>` : ''}
          ${m.session_id ? `<div>Session ID: <span class="text-slate-300">${escapeHtml(m.session_id)}</span></div>` : ''}
          ${m.uid ? `<div>UID Scope: <span class="text-slate-300">${escapeHtml(m.uid)}</span></div>` : ''}
          ${m.raw_vector_score !== undefined ? `<div>Raw Cosine Similarity: <span class="text-cyan-400">${escapeHtml(m.raw_vector_score)}</span></div>` : ''}
        </div>
      </details>
    </div>
  `).join('');

  // Attach delete / purge handlers
  container.querySelectorAll('.btn-forget-memory').forEach(btn => {
    btn.addEventListener('click', async () => {
      const pointId = btn.getAttribute('data-delete-id');
      const sessionId = btn.getAttribute('data-session-id');
      if (confirm('Permanently delete this memory record from Qdrant vector storage?')) {
        try {
          await api.forgetMemory(sessionId, pointId);
          showToast('Memory record purged from Qdrant');
          btn.closest('.omi-card').remove();
        } catch (err) {
          showToast('Purge failed: ' + err.message, 'warning');
        }
      }
    });
  });
}
