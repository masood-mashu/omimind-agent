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
            <span>âœ“ Key Decisions Confirmed</span>
          </h4>
          <ul class="text-xs text-slate-300 space-y-1.5 font-mono">
            ${s.key_decisions.map(d => `<li class="flex items-start gap-1.5"><span class="text-emerald-400">â€¢</span><span>${d}</span></li>`).join('')}
          </ul>
        </div>

        <div class="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          <h4 class="text-xs font-bold text-amber-400 uppercase tracking-wider mb-2 flex items-center gap-1.5 font-mono">
            <span>âš ï¸ Identified Risks & Blockers</span>
          </h4>
          <ul class="text-xs text-slate-300 space-y-1.5 font-mono">
            ${s.risks_and_blockers.map(r => `<li class="flex items-start gap-1.5"><span class="text-amber-400">â€¢</span><span>${r}</span></li>`).join('')}
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

// â”€â”€â”€ Agent Pipeline Live Visualization â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const AGENT_LABELS = {
  MemoryAgent:          { icon: 'ðŸ—„ï¸', label: 'Qdrant Memory Agent',       color: 'cyan' },
  ActionExtractor:      { icon: 'ðŸŽ¯', label: 'Lyzr Action Extractor',     color: 'amber' },
  ExecutiveSynthesizer: { icon: 'ðŸ§ ', label: 'Lyzr Executive Synthesizer', color: 'indigo' },
  TaskDispatcher:       { icon: 'ðŸ“¬', label: 'Lyzr Task Dispatcher',       color: 'emerald' }
};
const AGENT_ORDER = ['MemoryAgent', 'ActionExtractor', 'ExecutiveSynthesizer', 'TaskDispatcher'];

export function showPipelinePanel() {
  const panel = document.getElementById('pipeline-panel');
  if (!panel) return;
  panel.classList.remove('hidden');

  // Reset all rows to pending
  AGENT_ORDER.forEach(agent => {
    const row = document.getElementById(`pipeline-row-${agent}`);
    if (!row) return;
    const { color } = AGENT_LABELS[agent];
    row.innerHTML = _agentRow(agent, 'pending', '');
  });
}

export function updatePipelineAgent(event) {
  const { agent, status, message, count } = event;
  const row = document.getElementById(`pipeline-row-${agent}`);
  if (!row) return;
  row.innerHTML = _agentRow(agent, status, message, count);
}

function _agentRow(agent, status, message, count) {
  const { icon, label, color } = AGENT_LABELS[agent] || { icon: 'âš™ï¸', label: agent, color: 'slate' };

  const statusIcon = status === 'running'
    ? `<span class="w-2 h-2 rounded-full bg-${color}-400 animate-ping inline-block"></span>`
    : status === 'done'
    ? `<span class="text-emerald-400 font-bold">âœ“</span>`
    : `<span class="w-2 h-2 rounded-full bg-slate-700 inline-block"></span>`;

  const countBadge = (status === 'done' && count !== undefined)
    ? `<span class="ml-auto px-2 py-0.5 rounded-full text-[10px] font-mono bg-${color}-500/20 text-${color}-300 border border-${color}-500/30">${count}</span>`
    : '';

  const msgEl = message
    ? `<p class="text-[10px] text-slate-500 font-mono mt-0.5">${message}</p>`
    : '';

  return `
    <div class="flex items-start gap-2.5">
      <div class="mt-0.5 flex-shrink-0">${statusIcon}</div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <span class="text-xs font-semibold text-slate-200">${icon} ${label}</span>
          ${countBadge}
        </div>
        ${msgEl}
      </div>
    </div>`;
}
