/**
 * meetings.js - Meetings Overview & Directory View
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

export function renderMeetings(container) {
  const state = getState();
  const meetings = state.meetings || [];

  container.innerHTML = `
    <div class="view-container max-w-6xl mx-auto space-y-6 py-4 px-4 sm:px-6">
      
      <!-- Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-4">
        <div>
          <h1 class="text-xl sm:text-2xl font-bold text-white flex items-center gap-2.5">
            <span>📅</span>
            <span>Meeting Intelligence</span>
          </h1>
          <p class="text-xs sm:text-sm text-slate-400 mt-0.5">
            Autonomous multi-agent intelligence dossiers for executive, engineering, and academic sessions.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <button id="btn-seed-data" class="px-3.5 py-1.5 rounded-xl border border-white/10 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition">
            Reset Demo Sessions
          </button>
        </div>
      </div>

      <!-- Meetings Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        ${renderMeetingCards(meetings, state.activeDossier)}
      </div>

    </div>
  `;

  // Handlers: No manual onclick override needed since native <a> elements trigger hashchange router!
  const seedBtn = container.querySelector('#btn-seed-data');
  if (seedBtn) {
    seedBtn.addEventListener('click', async () => {
      seedBtn.disabled = true;
      seedBtn.innerText = 'Seeding Qdrant...';
      try {
        await api.seedDemoData();
        const meetingData = await api.fetchMeetings();
        state.meetings = meetingData.meetings || [];
        showToast('Demo meetings pre-seeded into Qdrant memory');
        renderMeetings(container);
      } catch (err) {
        showToast('Seed error: ' + err.message, 'warning');
      } finally {
        seedBtn.disabled = false;
        seedBtn.innerText = 'Reset Demo Sessions';
      }
    });
  }
}

function renderMeetingCards(meetings, activeDossier) {
  if (!meetings || meetings.length === 0) {
    return `
      <div class="col-span-full omi-card p-12 text-center text-slate-300 space-y-2">
        <p class="font-medium text-white">No meetings processed yet.</p>
        <p class="text-xs text-slate-400">Ambient sessions captured by Omi will automatically appear here.</p>
      </div>
    `;
  }

  return meetings.map(m => {
    const isProcessed = m.processed || (activeDossier && activeDossier.session_id === m.id);

    return `
      <a href="#meeting/${escapeHtml(m.id)}" class="omi-card omi-card-interactive p-5 flex flex-col justify-between space-y-4 border border-white/10 hover:border-cyan-500/30 transition group" aria-label="Meeting: ${escapeHtml(m.title)}">
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-mono-tech ${
              m.category?.includes('Executive') ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' :
              m.category?.includes('SRE') ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
              'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
            }">
              ${escapeHtml(m.category || 'Session')}
            </span>
            <span class="text-xs text-slate-400 font-mono-tech">${escapeHtml(m.duration || '')}</span>
          </div>

          <div>
            <h2 class="font-bold text-base text-white leading-snug group-hover:text-cyan-300 transition">
              ${escapeHtml(m.title)}
            </h2>
            <p class="text-xs text-slate-300 mt-1 line-clamp-1">
              ${m.participants && m.participants.length > 0 ? m.participants.map(escapeHtml).join(', ') : 'Participants'}
            </p>
          </div>

          <div class="flex items-center gap-2 pt-1 text-[11px] font-mono-tech text-slate-400">
            <span>${m.turns_count || 0} utterances</span>
            <span>•</span>
            <span class="${isProcessed ? 'text-emerald-400 font-semibold' : 'text-slate-400'}">
              ${isProcessed ? '✓ Intelligence Dossier Ready' : '○ Needs Ingestion'}
            </span>
          </div>
        </div>

        <div class="pt-3 border-t border-white/5 flex items-center justify-between">
          <span class="text-xs font-semibold text-cyan-400 flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
            <span>Open Intelligence Report</span>
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
          </span>
          <span class="text-[10px] text-slate-400 font-mono-tech">ID: ${escapeHtml(m.id)}</span>
        </div>
      </a>
    `;
  }).join('');
}
