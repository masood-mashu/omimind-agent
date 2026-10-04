/**
 * ui.js - Presentation & DOM Rendering Components (v2.1)
 * Enhanced with 5-Agent Swarm, Calendar Invites, and Tactile Feedback
 */

let lastDossier = null;

export function switchTab(tabId) {
  const tabs = ['summary', 'tasks', 'email', 'jira', 'calendar'];
  tabs.forEach(t => {
    const el = document.getElementById(`tab-${t}`);
    const btn = document.getElementById(`tab-${t}-btn`);
    if (el) el.classList.add('hidden');
    if (btn) btn.className = "px-4 py-2 rounded-xl text-sm font-semibold text-slate-400 hover:text-slate-200 transition";
  });

  const activeEl = document.getElementById(`tab-${tabId}`);
  const activeBtn = document.getElementById(`tab-${tabId}-btn`);
  if (activeEl) activeEl.classList.remove('hidden');
  if (activeBtn) activeBtn.className = "px-4 py-2 rounded-xl text-sm font-semibold bg-cyan-600/20 text-cyan-300 border border-cyan-500/30 transition shadow-sm shadow-cyan-500/10";
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

export function showToast(message, type = 'success') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  const borderCol = type === 'success' ? 'border-cyan-500/40' : 'border-amber-500/40';
  const textCol = type === 'success' ? 'text-cyan-300' : 'text-amber-300';
  toast.className = `toast pointer-events-auto px-4 py-2.5 rounded-xl bg-slate-900/95 border ${borderCol} ${textCol} text-xs font-mono shadow-2xl flex items-center gap-2 backdrop-blur-md`;
  toast.innerHTML = `<span class="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    setTimeout(() => toast.remove(), 300);
  }, 2800);
}

export function renderDossier(data) {
  lastDossier = data;

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
  if (summaryContainer && s) {
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
    if (!data.action_items || data.action_items.length === 0) {
      itemsList.innerHTML = `<p class="text-slate-500 text-xs">No explicit action items found.</p>`;
    } else {
      itemsList.innerHTML = data.action_items.map(item => `
        <div class="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 flex items-center justify-between hover:border-slate-700 transition">
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
      <div class="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1.5 hover:border-slate-700 transition">
        <div class="flex justify-between items-center text-xs">
          <span class="font-bold text-cyan-300 font-mono">${t.ticket_key}: ${t.summary}</span>
          <span class="text-slate-400 text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800">${t.priority} Priority</span>
        </div>
        <div class="text-slate-400 text-[11px] font-mono">Assignee: <span class="text-slate-200">${t.assignee}</span> | Due: <span class="text-slate-200">${t.due_date}</span></div>
        <div class="text-slate-500 text-[11px] italic font-sans">${t.description}</div>
      </div>
    `).join('');
  }

  // 5. Calendar Sync Tab (Agent 5)
  const calList = document.getElementById('calendar-events-list');
  if (calList) {
    const events = data.calendar_events || [];
    if (events.length === 0) {
      calList.innerHTML = `
        <div class="p-6 rounded-xl border border-dashed border-slate-800 text-center text-slate-500 text-xs">
          No explicit scheduling commitments were detected in this transcript.
        </div>`;
    } else {
      calList.innerHTML = events.map((evt, idx) => `
        <div class="p-4 rounded-xl bg-slate-900/90 border border-indigo-500/20 flex flex-col md:flex-row justify-between md:items-center gap-3 hover:border-indigo-500/40 transition">
          <div class="space-y-1 max-w-[70%]">
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">CALENDAR SYNC</span>
              <span class="font-semibold text-xs text-white">${evt.title}</span>
            </div>
            <p class="text-[11px] text-slate-400 italic font-mono">Proposed by ${evt.speaker_source}: "${evt.context_utterance}"</p>
            <div class="text-[11px] text-cyan-300 font-mono flex items-center gap-3">
              <span>📅 ${evt.date_str}</span>
              <span>⏰ ${evt.time_str} (${evt.duration_minutes}m)</span>
            </div>
          </div>
          <div class="flex items-center gap-2 font-mono text-xs">
            <a href="${evt.google_calendar_url}" target="_blank" class="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs flex items-center gap-1.5 transition">
              <span>+ Google Meet</span>
            </a>
            <button onclick="downloadICS(${idx})" class="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition">
              .ics File
            </button>
          </div>
        </div>
      `).join('');
    }
  }
}

export function openGmailCompose() {
  const subEl = document.getElementById('email-subject');
  const toEl = document.getElementById('email-to');
  const bodyEl = document.getElementById('email-body');
  
  const to = (toEl && toEl.innerText) ? toEl.innerText.trim() : '';
  const subject = (subEl && subEl.innerText) ? subEl.innerText.trim() : 'Executive Follow-Up';
  const body = (bodyEl && bodyEl.innerText) ? bodyEl.innerText.trim() : '';

  if (!body || body === 'No email generated yet.') {
    showToast('No email generated yet. Run the swarm first!');
    return;
  }

  const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(to)}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  window.open(gmailUrl, '_blank');
  showToast('Opening Gmail with pre-filled draft...');
}

export function openMailto() {
  const subEl = document.getElementById('email-subject');
  const toEl = document.getElementById('email-to');
  const bodyEl = document.getElementById('email-body');
  
  const to = (toEl && toEl.innerText) ? toEl.innerText.trim() : '';
  const subject = (subEl && subEl.innerText) ? subEl.innerText.trim() : 'Executive Follow-Up';
  const body = (bodyEl && bodyEl.innerText) ? bodyEl.innerText.trim() : '';

  if (!body || body === 'No email generated yet.') {
    showToast('No email generated yet. Run the swarm first!');
    return;
  }

  const mailtoUrl = `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  window.location.href = mailtoUrl;
  showToast('Opening default mail client...');
}

export function copyEmailText() {
  const body = document.getElementById('email-body');
  if (body && body.innerText) {
    navigator.clipboard.writeText(body.innerText).then(() => {
      showToast('Follow-up email copied to clipboard!');
    });
  }
}

export function copyJiraText() {
  if (lastDossier && lastDossier.jira_tickets) {
    const text = JSON.stringify(lastDossier.jira_tickets, null, 2);
    navigator.clipboard.writeText(text).then(() => {
      showToast('Jira ticket payloads copied to clipboard!');
    });
  }
}

export function downloadICS(index) {
  if (lastDossier && lastDossier.calendar_events && lastDossier.calendar_events[index]) {
    const evt = lastDossier.calendar_events[index];
    const blob = new Blob([evt.ics_data || ''], { type: 'text/calendar;charset=utf-8' });
    const link = document.createElement('a');
    link.href = window.URL.createObjectURL(blob);
    link.setAttribute('download', `${evt.id || 'meeting'}.ics`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    showToast(`Downloaded ${evt.title} (.ics)`);
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

// ─── Agent Pipeline Live Visualization (5 Agents) ─────────────────────────────

const AGENT_LABELS = {
  MemoryAgent:          { icon: '🗄️', label: 'Qdrant Memory Agent',       color: 'cyan' },
  ActionExtractor:      { icon: '🎯', label: 'Lyzr Action Extractor',     color: 'amber' },
  ExecutiveSynthesizer: { icon: '🧠', label: 'Lyzr Executive Synthesizer', color: 'indigo' },
  TaskDispatcher:       { icon: '📬', label: 'Lyzr Task Dispatcher',       color: 'emerald' },
  CalendarScheduler:    { icon: '📅', label: 'Lyzr Calendar Scheduler',    color: 'violet' }
};
const AGENT_ORDER = ['MemoryAgent', 'ActionExtractor', 'ExecutiveSynthesizer', 'TaskDispatcher', 'CalendarScheduler'];

export function showPipelinePanel() {
  const panel = document.getElementById('pipeline-panel');
  if (!panel) return;
  panel.classList.remove('hidden');

  AGENT_ORDER.forEach(agent => {
    const row = document.getElementById(`pipeline-row-${agent}`);
    if (!row) return;
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
  const { icon, label, color } = AGENT_LABELS[agent] || { icon: '⚙️', label: agent, color: 'slate' };

  const statusIcon = status === 'running'
    ? `<span class="w-2.5 h-2.5 rounded-full bg-${color}-400 animate-ping inline-block"></span>`
    : status === 'done'
    ? `<span class="text-emerald-400 font-bold">✓</span>`
    : `<span class="w-2.5 h-2.5 rounded-full bg-slate-700 inline-block"></span>`;

  const countBadge = (status === 'done' && count !== undefined)
    ? `<span class="ml-auto px-2 py-0.5 rounded-full text-[10px] font-mono bg-${color}-500/20 text-${color}-300 border border-${color}-500/30">${count}</span>`
    : '';

  const msgEl = message
    ? `<p class="text-[10px] text-slate-400 font-mono mt-0.5">${message}</p>`
    : '';

  return `
    <div class="flex items-start gap-2.5">
      <div class="mt-0.5 flex-shrink-0">${statusIcon}</div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <span class="text-xs font-semibold text-slate-200 font-mono">${icon} ${label}</span>
          ${countBadge}
        </div>
        ${msgEl}
      </div>
    </div>`;
}
