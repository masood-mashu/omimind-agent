/**
 * ui.js - Presentation & DOM Rendering Components
 */

export function switchTab(tabId) {
  const tabs = ['summary', 'tasks', 'email', 'jira'];
  tabs.forEach(t => {
    const el = document.getElementById(`tab-${t}`);
    const btn = document.getElementById(`tab-${t}-btn`);
    if (el) el.classList.add('hidden');
    if (btn) btn.className = "px-4 py-2 rounded-xl text-sm font-semibold text-slate-400 hover:text-slate-200 transition";
  });

  const activeEl = document.getElementById(`tab-${tabId}`);
  const activeBtn = document.getElementById(`tab-${tabId}-btn`);
  if (activeEl) activeEl.classList.remove('hidden');
  if (activeBtn) activeBtn.className = "px-4 py-2 rounded-xl text-sm font-semibold bg-cyan-600/20 text-cyan-300 border border-cyan-500/30 transition";
}

export function updateMeetingButtons(activeId) {
  const meetings = ['q4_strategy', 'sre_postmortem', 'cs_lecture'];
  meetings.forEach(m => {
    const btn = document.getElementById(`btn-${m}`);
    if (!btn) return;
    if (m === activeId) {
      btn.className = "w-full text-left p-3.5 rounded-xl border border-cyan-500/40 bg-cyan-500/10 transition flex flex-col gap-1 hover:border-cyan-400";
    } else {
      btn.className = "w-full text-left p-3.5 rounded-xl border border-slate-800 bg-slate-900/40 transition flex flex-col gap-1 hover:border-slate-700";
    }
  });
}

export function renderDossier(data) {
  // Update Qdrant vector badges
  const badge = document.getElementById('vectors-indexed-badge');
  const countSpan = document.getElementById('indexed-count');
  if (badge && countSpan) {
    badge.classList.remove('hidden');
    countSpan.innerText = data.indexed_vectors_count;
  }

  // 1. Executive Synthesis Tab
  const s = data.summary;
  const summaryContainer = document.getElementById('summary-content');
  if (summaryContainer) {
    summaryContainer.innerHTML = `
      <div>
        <div class="flex justify-between items-start mb-2">
          <h2 class="text-xl font-bold text-white">${s.title}</h2>
          <span class="text-xs px-2.5 py-1 rounded-full bg-cyan-500/20 text-cyan-300 font-mono">~${s.estimated_duration_min} min session</span>
        </div>
        <p class="text-xs text-slate-400 font-mono mb-4">Attendees: ${s.participants.join(', ')}</p>
        <div class="p-4 rounded-xl bg-slate-900/80 border border-slate-800 text-slate-200 text-sm leading-relaxed mb-4">
          ${s.executive_summary}
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          <h4 class="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-1.5 font-mono">
            <span>✓ Key Decisions Confirmed</span>
          </h4>
          <ul class="text-xs text-slate-300 space-y-1.5 font-mono">
            ${s.key_decisions.map(d => `<li class="flex items-start gap-1.5"><span class="text-emerald-400">•</span><span>${d}</span></li>`).join('')}
          </ul>
        </div>

        <div class="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          <h4 class="text-xs font-bold text-amber-400 uppercase tracking-wider mb-2 flex items-center gap-1.5 font-mono">
            <span>⚠️ Identified Risks & Blockers</span>
          </h4>
          <ul class="text-xs text-slate-300 space-y-1.5 font-mono">
            ${s.risks_and_blockers.map(r => `<li class="flex items-start gap-1.5"><span class="text-amber-400">•</span><span>${r}</span></li>`).join('')}
          </ul>
        </div>
      </div>
    `;
  }

  // 2. Action Items Tab
  const itemsList = document.getElementById('action-items-list');
  if (itemsList) {
    if (data.action_items.length === 0) {
      itemsList.innerHTML = `<p class="text-slate-500 text-xs">No explicit action items found.</p>`;
    } else {
      itemsList.innerHTML = data.action_items.map(item => `
        <div class="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 flex items-center justify-between">
          <div class="space-y-1 max-w-[70%]">
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                item.priority === 'Critical' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
                item.priority === 'High' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'bg-slate-800 text-slate-300'
              }">${item.priority}</span>
              <span class="font-semibold text-xs text-white">${item.title}</span>
            </div>
            <p class="text-[11px] text-slate-400 truncate italic">"${item.quote}"</p>
          </div>
          <div class="text-right font-mono text-xs">
            <span class="text-cyan-400 block font-bold">${item.assignee}</span>
            <span class="text-slate-500 text-[10px]">Due: ${item.due_date}</span>
          </div>
        </div>
      `).join('');
    }
  }

  // 3. Email Draft Tab
  const subEl = document.getElementById('email-subject');
  const toEl = document.getElementById('email-to');
  const bodyEl = document.getElementById('email-body');
  if (subEl && toEl && bodyEl && data.email_draft) {
    subEl.innerText = data.email_draft.subject;
    toEl.innerText = data.email_draft.to;
    bodyEl.innerText = data.email_draft.body;
  }

  // 4. Jira Tickets Tab
  const jiraList = document.getElementById('jira-tickets-list');
  if (jiraList && data.jira_tickets) {
    jiraList.innerHTML = data.jira_tickets.map(t => `
      <div class="p-3 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1">
        <div class="flex justify-between items-center text-xs">
          <span class="font-bold text-cyan-300">${t.ticket_key}: ${t.summary}</span>
          <span class="text-slate-400 text-[10px]">${t.priority} Priority</span>
        </div>
        <div class="text-slate-400 text-[11px]">Assignee: <span class="text-slate-200">${t.assignee}</span> | Due: <span class="text-slate-200">${t.due_date}</span></div>
        <div class="text-slate-500 text-[10px] italic">${t.description}</div>
      </div>
    `).join('');
  }
}

export function renderQueryResult(data) {
  const box = document.getElementById('query-result-box');
  const score = document.getElementById('query-score');
  const answer = document.getElementById('query-answer');
  if (box && score && answer) {
    box.classList.remove('hidden');
    score.innerText = `${Math.round(data.relevance_top * 100)}% Match`;
    answer.innerText = data.answer;
  }
}
