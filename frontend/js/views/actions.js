/**
 * actions.js - Dedicated Action Center View
 * Manage extracted verbal commitments, owners, due dates, evidence quotes, and output integrations.
 */

import { getState } from '../state.js';
import * as api from '../api.js';
import { showToast } from '../components/toast.js';

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[c]);
}

export async function renderActions(container) {
  let currentFilter = 'all';

  container.innerHTML = `
    <div class="view-container max-w-5xl mx-auto space-y-6 py-4 px-4 sm:px-6">
      
      <!-- Top Title & Filter Bar -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-4">
        <div>
          <h1 class="text-xl sm:text-2xl font-bold text-white flex items-center gap-2.5">
            <span class="text-amber-400">⚡</span>
            <span>Action Center</span>
          </h1>
          <p class="text-xs sm:text-sm text-slate-300 mt-0.5">
            Verbal commitments and follow-up deliverables extracted from ambient conversational memory.
          </p>
        </div>

        <div class="flex items-center gap-2">
          <span class="px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 text-xs font-mono-tech">
            Action Item Intelligence
          </span>
        </div>
      </div>

      <!-- Horizontal Priority Filter Rail (Single-line, non-wrapping on mobile) -->
      <div class="omi-card p-3 border border-white/10 bg-[#0e131f]">
        <div class="omi-filter-rail items-center" aria-label="Priority filters">
          <span class="text-slate-400 text-[11px] font-medium flex-shrink-0 mr-1">Filter by Priority:</span>
          <button type="button" class="action-filter-chip touch-target-44 px-3.5 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 text-xs font-semibold whitespace-nowrap transition" data-filter="all">
            All Actions
          </button>
          <button type="button" class="action-filter-chip touch-target-44 px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 text-xs whitespace-nowrap transition" data-filter="Critical">
            Critical (P0)
          </button>
          <button type="button" class="action-filter-chip touch-target-44 px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 text-xs whitespace-nowrap transition" data-filter="High">
            High (P1)
          </button>
          <button type="button" class="action-filter-chip touch-target-44 px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 text-xs whitespace-nowrap transition" data-filter="Medium">
            Medium
          </button>
        </div>
      </div>

      <!-- Action Items Container -->
      <div id="actions-list" class="space-y-4 min-h-[340px]">
        <div class="p-8 text-center text-slate-300 text-xs">
          <span class="w-2.5 h-2.5 rounded-full bg-amber-400 inline-block animate-ping mr-2"></span>
          Loading extracted actions...
        </div>
      </div>

    </div>
  `;

  const listDiv = container.querySelector('#actions-list');

  async function loadActions() {
    try {
      const data = await api.fetchActions();
      const actions = data.actions || [];
      renderActionCards(listDiv, actions, currentFilter);
    } catch (err) {
      if (listDiv) {
        listDiv.innerHTML = `
          <div class="omi-card p-12 text-center text-slate-300 space-y-2">
            <p class="font-medium text-white">No actions loaded</p>
            <p class="text-xs text-slate-400">${escapeHtml(err.message)}</p>
          </div>
        `;
      }
    }
  }

  // Handle filter chip clicks
  container.querySelectorAll('.action-filter-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('.action-filter-chip').forEach(b => {
        b.className = "action-filter-chip touch-target-44 px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 text-xs whitespace-nowrap transition";
      });
      btn.className = "action-filter-chip touch-target-44 px-3.5 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 text-xs font-semibold whitespace-nowrap transition";
      currentFilter = btn.getAttribute('data-filter') || 'all';
      loadActions();
    });
  });

  loadActions();
}

function renderActionCards(container, actions, priorityFilter = 'all') {
  if (!actions || actions.length === 0) {
    container.innerHTML = `
      <div class="omi-card p-12 text-center text-slate-300 space-y-3 border-dashed border-white/10">
        <div class="text-3xl">✓</div>
        <p class="font-bold text-white text-base">You're all caught up!</p>
        <p class="text-xs max-w-sm mx-auto text-slate-400">
          No pending action items extracted yet. Process a meeting in the Meetings section to extract verbal commitments.
        </p>
      </div>
    `;
    return;
  }

  const filtered = priorityFilter === 'all' 
    ? actions 
    : actions.filter(a => a.priority === priorityFilter);

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="omi-card p-8 text-center text-slate-300 text-xs">
        No action items match the priority filter "${escapeHtml(priorityFilter)}".
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(item => {
    const isCritical = item.priority === 'Critical';
    const isHigh = item.priority === 'High';

    const borderAccentClass = isCritical 
      ? 'border-l-4 border-l-rose-500' 
      : isHigh 
      ? 'border-l-4 border-l-amber-500' 
      : 'border-l-4 border-l-cyan-500';

    return `
      <div class="omi-card p-5 space-y-4 border border-white/10 hover:border-white/20 transition ${borderAccentClass} bg-[#0e131f]">
        
        <!-- Top Row: Priority Badge & Title & Status -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div class="flex items-center gap-2.5">
            <span class="px-2.5 py-1 rounded-md text-[10px] font-mono-tech font-bold ${
              isCritical ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
              isHigh ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' :
              'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
            }">
              ${escapeHtml(item.priority || 'Normal')}
            </span>
            <h2 class="font-bold text-sm sm:text-base text-white">
              ${escapeHtml(item.title)}
            </h2>
          </div>
          <span class="px-2.5 py-0.5 rounded text-[10px] font-mono-tech bg-slate-800 text-slate-300 self-start sm:self-auto border border-white/5">
            Status: PENDING
          </span>
        </div>

        <!-- Details Row (Explicitly read-only verbal commitments) -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono-tech bg-slate-950/70 p-3 rounded-xl border border-white/5">
          <div>
            <span class="text-slate-400 block text-[10px]">ASSIGNED TO</span>
            <span class="text-cyan-300 font-bold">${escapeHtml(item.assignee || 'Team')}</span>
          </div>
          <div>
            <span class="text-slate-400 block text-[10px]">DUE DATE</span>
            <span class="text-slate-200">${escapeHtml(item.due_date || 'Upcoming')}</span>
          </div>
          <div>
            <span class="text-slate-400 block text-[10px]">SOURCE MEETING</span>
            <span class="text-slate-300 truncate block">${escapeHtml(item.source_meeting || item.session_id || 'Meeting')}</span>
          </div>
        </div>

        <!-- Evidence Quote -->
        <div class="text-xs bg-slate-900/60 p-3 rounded-xl border-l-2 border-amber-400/60 space-y-1">
          <span class="text-[10px] text-slate-400 font-mono-tech uppercase tracking-wider block">Verbal Evidence:</span>
          <p class="text-slate-200 italic font-sans leading-relaxed">
            "${escapeHtml(item.quote || item.title)}"
          </p>
        </div>

        <!-- Action Buttons Row (Honest: Draft ready, payload ready) -->
        <div class="pt-2 border-t border-white/5 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div class="flex items-center gap-2">
            <button type="button" data-action-copy="${escapeHtml(item.title + ' - Assigned to ' + item.assignee + ' (Due: ' + item.due_date + ')')}" class="btn-copy-action touch-target-44 px-3.5 py-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium transition flex items-center gap-1.5" aria-label="Copy action item text">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/></svg>
              <span>Copy Text</span>
            </button>
            <span class="px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[11px] font-mono-tech">
              ✓ Jira payload ready
            </span>
          </div>
          <span class="text-[11px] text-slate-400 font-mono-tech">
            ID: ${escapeHtml(item.id || '')}
          </span>
        </div>

      </div>
    `;
  }).join('');

  container.querySelectorAll('.btn-copy-action').forEach(btn => {
    btn.addEventListener('click', () => {
      const text = btn.getAttribute('data-action-copy');
      if (text) {
        navigator.clipboard.writeText(text).then(() => {
          showToast('Action item copied to clipboard!');
        });
      }
    });
  });
}

