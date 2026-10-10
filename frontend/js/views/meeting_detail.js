/**
 * meeting_detail.js - Meeting Intelligence Report View
 * Executive synthesis, confirmed decisions, risks, actions, calendar sync, email/Jira, and raw transcript.
 */

import { getState, setState, addPipelineEvent } from '../state.js';
import * as api from '../api.js';
import { navigate } from '../router.js';
import { showToast } from '../components/toast.js';

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[c]);
}

function safeUrl(value) {
  try {
    const url = new URL(String(value ?? ''), window.location.origin);
    return ['http:', 'https:'].includes(url.protocol) ? escapeHtml(url.href) : '#';
  } catch (_) {
    return '#';
  }
}

export async function renderMeetingDetail(container, meetingId) {
  container.innerHTML = `
    <div class="view-container max-w-5xl mx-auto py-4 px-4 sm:px-6">
      <div class="p-8 text-center text-slate-400 text-xs">
        <span class="w-3 h-3 rounded-full bg-cyan-400 inline-block animate-ping mr-2"></span>
        Loading meeting intelligence...
      </div>
    </div>
  `;

  try {
    const data = await api.fetchMeetingDetail(meetingId);
    renderContent(container, data);
  } catch (err) {
    container.innerHTML = `
      <div class="view-container max-w-5xl mx-auto py-8 px-4 text-center space-y-4">
        <h2 class="text-lg font-bold text-white">Meeting Not Found</h2>
        <p class="text-xs text-slate-400">${escapeHtml(err.message)}</p>
        <button id="btn-back-to-meetings" class="px-4 py-2 rounded-xl bg-slate-800 text-cyan-300 text-xs font-semibold">
          ← Back to Meetings
        </button>
      </div>
    `;
    const backBtn = container.querySelector('#btn-back-to-meetings');
    if (backBtn) backBtn.addEventListener('click', () => navigate('meetings'));
  }
}

function renderContent(container, meeting) {
  const state = getState();
  const dossier = meeting.dossier || (state.activeDossier?.session_id === meeting.id ? state.activeDossier : null);
  const isProcessed = Boolean(dossier);
  const summary = dossier?.summary;
  const actionItems = dossier?.action_items || [];
  const calendarEvents = dossier?.calendar_events || [];
  const emailDraft = dossier?.email_draft;
  const jiraTickets = dossier?.jira_tickets || [];
  const transcriptLines = meeting.lines || [];

  container.innerHTML = `
    <div class="view-container max-w-5xl mx-auto space-y-8 py-4 px-4 sm:px-6">
      
      <!-- Top Navigation & Action -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-4">
        <div class="flex items-center gap-3">
          <a href="#meetings" id="btn-back" class="touch-target-44 p-2 rounded-xl bg-slate-900 border border-white/10 hover:border-white/20 text-slate-300 hover:text-white transition flex items-center justify-center" aria-label="Back to meetings list">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
          </a>
          <div>
            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-mono-tech ${
              meeting.category?.includes('Executive') ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' :
              meeting.category?.includes('SRE') ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
              'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
            }">
              ${escapeHtml(meeting.category || 'Session')}
            </span>
            <h1 class="text-xl sm:text-2xl font-bold text-white mt-1">
              ${escapeHtml(meeting.title)}
            </h1>
          </div>
        </div>

        <div class="flex items-center gap-2.5">
          <button 
            id="btn-run-pipeline"
            class="touch-target-44 px-4 py-2.5 rounded-xl font-semibold text-xs text-white bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 shadow-md shadow-cyan-600/20 transition flex items-center gap-2"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/></svg>
            <span id="pipeline-btn-text">${isProcessed ? 'Re-run Intelligence Pipeline' : 'Run Intelligence Pipeline'}</span>
          </button>
        </div>
      </div>

      <!-- Live Stream Execution Drawer (Shows during pipeline execution) -->
      <div id="meeting-pipeline-drawer" class="hidden omi-card p-4 space-y-3 border border-cyan-500/30 bg-[#0e131f] shadow-lg" role="status" aria-live="polite">
        <div class="flex items-center justify-between text-xs text-cyan-300 font-bold font-mono-tech">
          <span class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
            Multi-Agent Execution Pipeline Active
          </span>
          <span id="pipeline-status-text">Processing stream...</span>
        </div>
        <div id="pipeline-stages" class="space-y-2 text-xs font-mono-tech">
          <!-- Populated by SSE events -->
        </div>
      </div>

      <!-- Session Meta Pills -->
      <div class="flex flex-wrap items-center gap-3 text-xs text-slate-300 font-mono-tech">
        <span class="px-3 py-1 rounded-xl bg-slate-900 border border-white/5">
          ⏱ ${escapeHtml(meeting.duration || 'Session')}
        </span>
        <span class="px-3 py-1 rounded-xl bg-slate-900 border border-white/5">
          👥 ${meeting.participants ? meeting.participants.length : 0} Attendees: ${meeting.participants && meeting.participants.length > 0 ? meeting.participants.map(escapeHtml).join(', ') : ''}
        </span>
        <span class="px-3 py-1 rounded-xl bg-slate-900 border border-white/5">
          💬 ${transcriptLines.length} utterances
        </span>
      </div>

      <!-- Navigation Sections -->
      <div class="space-y-6">

        <!-- 1. Executive Synthesis & AI Summary -->
        <section class="omi-card p-6 space-y-4 border border-white/10">
          <div class="flex items-center justify-between border-b border-white/5 pb-3">
            <div class="flex items-center gap-2">
              <span class="text-cyan-400 font-bold">📋</span>
              <h2 class="text-base font-bold text-white">Executive Synthesis & Takeaways</h2>
            </div>
            <span class="text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 font-mono-tech">
              Synthesized by Lyzr Manager
            </span>
          </div>

          ${isProcessed && summary ? `
            <div class="p-4 rounded-xl bg-slate-950/70 border border-white/5 text-slate-200 text-sm leading-relaxed">
              ${escapeHtml(summary.executive_summary || 'Executive summary unavailable.')}
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <!-- Decisions -->
              <div class="p-4 rounded-xl bg-slate-950/50 border border-emerald-500/20 space-y-2">
                <h3 class="text-xs font-bold text-emerald-400 uppercase tracking-wider font-mono-tech flex items-center gap-1.5">
                  <span>✓ Key Decisions Confirmed</span>
                </h3>
                <ul class="text-xs text-slate-200 space-y-2 font-mono-tech">
                  ${(summary.key_decisions || []).map(d => `
                    <li class="flex items-start gap-2">
                      <span class="text-emerald-400 font-bold">•</span>
                      <span>${escapeHtml(d)}</span>
                    </li>
                  `).join('')}
                </ul>
              </div>

              <!-- Risks -->
              <div class="p-4 rounded-xl bg-slate-950/50 border border-amber-500/20 space-y-2">
                <h3 class="text-xs font-bold text-amber-400 uppercase tracking-wider font-mono-tech flex items-center gap-1.5">
                  <span>⚠️ Identified Risks & Blockers</span>
                </h3>
                <ul class="text-xs text-slate-200 space-y-2 font-mono-tech">
                  ${(summary.risks_and_blockers || []).map(r => `
                    <li class="flex items-start gap-2">
                      <span class="text-amber-400 font-bold">•</span>
                      <span>${escapeHtml(r)}</span>
                    </li>
                  `).join('')}
                </ul>
              </div>
            </div>
          ` : `
            <div class="p-8 text-center text-slate-400 text-xs border border-dashed border-white/10 rounded-xl space-y-2">
              <p class="font-medium text-white">Pipeline not executed yet for this meeting.</p>
              <p>Click "Run Intelligence Pipeline" above to extract decisions, risks, and commitments in real-time.</p>
            </div>
          `}
        </section>

        <!-- 2. Action Items -->
        <section class="omi-card p-6 space-y-4 border border-white/10">
          <div class="flex items-center justify-between border-b border-white/5 pb-3">
            <div class="flex items-center gap-2">
              <span class="text-amber-400 font-bold">⚡</span>
              <h2 class="text-base font-bold text-white">Extracted Action Items</h2>
            </div>
            <span class="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-300 font-mono-tech">
              Action Extractor (6ac578bf4b079480ed4ea5a5)
            </span>
          </div>

          <div class="space-y-3">
            ${isProcessed && actionItems.length > 0 ? actionItems.map(item => `
              <div class="p-4 rounded-xl bg-slate-950/60 border border-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-white/10 transition">
                <div class="space-y-1 max-w-[80%]">
                  <div class="flex items-center gap-2">
                    <span class="px-2 py-0.5 rounded text-[10px] font-mono-tech font-bold ${
                      item.priority === 'Critical' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
                      item.priority === 'High' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'bg-slate-800 text-slate-300'
                    }">${escapeHtml(item.priority)}</span>
                    <span class="font-semibold text-xs text-white">${escapeHtml(item.title)}</span>
                  </div>
                  <p class="text-[11px] text-slate-400 italic">"${escapeHtml(item.quote || item.title)}"</p>
                </div>
                <div class="text-right text-xs font-mono-tech flex-shrink-0">
                  <span class="text-cyan-400 block font-bold">${escapeHtml(item.assignee || 'Team')}</span>
                  <span class="text-slate-400 text-[10px]">Due: ${escapeHtml(item.due_date || 'Upcoming')}</span>
                </div>
              </div>
            `).join('') : `
              <div class="p-6 text-center text-slate-400 text-xs border border-dashed border-white/10 rounded-xl">
                ${isProcessed ? 'No explicit action items found in this transcript.' : 'Run the intelligence pipeline to extract commitments.'}
              </div>
            `}
          </div>
        </section>

        <!-- 3. Calendar Sync Suggestions -->
        <section class="omi-card p-6 space-y-4 border border-white/10">
          <div class="flex items-center justify-between border-b border-white/5 pb-3">
            <div class="flex items-center gap-2">
              <span class="text-indigo-400 font-bold">📅</span>
              <h2 class="text-base font-bold text-white">Calendar Commitments & Sync</h2>
            </div>
            <span class="text-xs px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 font-mono-tech">
              RFC 5545 & Google Calendar Ready
            </span>
          </div>

          <div class="space-y-3">
            ${isProcessed && calendarEvents.length > 0 ? calendarEvents.map((evt, idx) => `
              <div class="p-4 rounded-xl bg-slate-950/60 border border-indigo-500/20 flex flex-col md:flex-row justify-between md:items-center gap-3">
                <div class="space-y-1">
                  <div class="flex items-center gap-2">
                    <span class="px-2 py-0.5 rounded text-[10px] font-mono-tech bg-indigo-500/20 text-indigo-300">CALENDAR EVENT</span>
                    <span class="font-semibold text-xs text-white">${escapeHtml(evt.title)}</span>
                  </div>
                  <p class="text-[11px] text-slate-400 italic">Proposed by ${escapeHtml(evt.speaker_source)}: "${escapeHtml(evt.context_utterance)}"</p>
                  <div class="text-[11px] text-cyan-300 font-mono-tech flex items-center gap-3">
                    <span>📅 ${escapeHtml(evt.date_str)}</span>
                    <span>⏰ ${escapeHtml(evt.time_str)} (${escapeHtml(evt.duration_minutes)}m)</span>
                  </div>
                </div>
                <div class="flex items-center gap-2 font-mono-tech text-xs">
                  <a href="${safeUrl(evt.google_calendar_url)}" target="_blank" rel="noopener noreferrer" class="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs flex items-center gap-1.5 transition">
                    Open in Google Calendar (Draft)
                  </a>
                  <button data-ics-idx="${idx}" class="btn-ics-download px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition">
                    Download .ics
                  </button>
                </div>
              </div>
            `).join('') : `
              <div class="p-6 text-center text-slate-400 text-xs border border-dashed border-white/10 rounded-xl">
                ${isProcessed ? 'No scheduling commitments detected in this session.' : 'Run the pipeline to detect follow-up meetings.'}
              </div>
            `}
          </div>
        </section>

        <!-- 4. Follow-up Draft Outputs (Email & Jira) -->
        <section class="omi-card p-6 space-y-4 border border-white/10">
          <div class="flex items-center justify-between border-b border-white/5 pb-3">
            <div class="flex items-center gap-2">
              <span class="text-rose-400 font-bold">📬</span>
              <h2 class="text-base font-bold text-white">Follow-up Drafts & Jira Payloads</h2>
            </div>
            <span class="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono-tech">
              User-Controlled Execution
            </span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            <!-- Email Draft -->
            <div class="p-4 rounded-xl bg-slate-950/60 border border-white/5 space-y-3 flex flex-col justify-between">
              <div class="space-y-2">
                <div class="flex items-center justify-between">
                  <span class="font-bold text-xs text-white">Executive Follow-Up Email Draft</span>
                  <span class="text-[10px] text-slate-400 font-mono-tech">${emailDraft ? 'Draft Ready' : 'Pending'}</span>
                </div>
                ${emailDraft ? `
                  <div class="text-[11px] font-mono-tech text-slate-400">
                    <div>Subject: <span class="text-slate-200">${escapeHtml(emailDraft.subject)}</span></div>
                    <div>To: <span class="text-cyan-300">${escapeHtml(emailDraft.to)}</span></div>
                  </div>
                  <pre class="p-3 rounded-lg bg-slate-900 border border-white/5 text-[11px] font-mono-tech text-slate-300 max-h-32 overflow-y-auto whitespace-pre-wrap">${escapeHtml(emailDraft.body)}</pre>
                ` : `
                  <p class="text-xs text-slate-400">No email draft generated yet.</p>
                `}
              </div>
              ${emailDraft ? `
                <div class="flex items-center gap-2 pt-2 border-t border-white/5">
                  <button id="btn-open-gmail" class="flex-1 py-1.5 px-2.5 rounded-lg bg-rose-600/20 border border-rose-500/30 text-rose-300 hover:bg-rose-600/30 text-xs font-semibold transition">
                    Open in Gmail (Draft)
                  </button>
                  <button id="btn-copy-email" class="py-1.5 px-2.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition">
                    Copy Draft
                  </button>
                </div>
              ` : ''}
            </div>

            <!-- Jira Tickets -->
            <div class="p-4 rounded-xl bg-slate-950/60 border border-white/5 space-y-3 flex flex-col justify-between">
              <div class="space-y-2">
                <div class="flex items-center justify-between">
                  <span class="font-bold text-xs text-white">Jira Payload Ready for Review</span>
                  <span class="text-[10px] text-slate-400 font-mono-tech">${jiraTickets.length} Payloads Ready</span>
                </div>
                ${jiraTickets.length > 0 ? `
                  <div class="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                    ${jiraTickets.map(t => `
                      <div class="p-2 rounded bg-slate-900 border border-white/5 text-[11px] font-mono-tech">
                        <span class="text-cyan-300 font-bold">${escapeHtml(t.ticket_key)}:</span> ${escapeHtml(t.summary)}
                      </div>
                    `).join('')}
                  </div>
                ` : `
                  <p class="text-xs text-slate-400">No Jira payloads generated yet.</p>
                `}
              </div>
              ${jiraTickets.length > 0 ? `
                <div class="flex items-center gap-2 pt-2 border-t border-white/5">
                  <button id="btn-copy-jira" class="w-full py-1.5 px-2.5 rounded-lg border border-cyan-500/30 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 text-xs font-semibold transition">
                    Copy Jira JSON Payloads
                  </button>
                </div>
              ` : ''}
            </div>

          </div>
        </section>

        <!-- 5. Complete Raw Transcript -->
        <section class="omi-card p-6 space-y-4 border border-white/10">
          <div class="flex items-center justify-between border-b border-white/5 pb-3">
            <div class="flex items-center gap-2">
              <span class="text-slate-400 font-bold">🎙</span>
              <h2 class="text-base font-bold text-white">Full Session Transcript</h2>
            </div>
            <span class="text-xs text-slate-400 font-mono-tech">
              ${transcriptLines.length} utterances with timestamps
            </span>
          </div>

          <div class="space-y-2.5 max-h-96 overflow-y-auto pr-2 custom-scrollbar">
            ${transcriptLines.map(line => `
              <div class="p-3 rounded-xl bg-slate-950/40 border border-white/5 flex items-start gap-3 text-xs">
                <span class="text-[10px] text-cyan-400 font-mono-tech flex-shrink-0 pt-0.5">
                  [${escapeHtml(line.timestamp_str || '00:00')}]
                </span>
                <div class="space-y-0.5">
                  <span class="font-bold text-slate-200 font-mono-tech">${escapeHtml(line.speaker || 'Speaker')}:</span>
                  <p class="text-slate-300 font-sans leading-relaxed">${escapeHtml(line.text)}</p>
                </div>
              </div>
            `).join('')}
          </div>
        </section>

      </div>

    </div>
  `;

  // Attach interactive listeners
  const backBtn = container.querySelector('#btn-back');
  if (backBtn) backBtn.addEventListener('click', () => navigate('meetings'));

  const pipelineBtn = container.querySelector('#btn-run-pipeline');
  const drawer = container.querySelector('#meeting-pipeline-drawer');
  const stagesDiv = container.querySelector('#pipeline-stages');
  const statusText = container.querySelector('#pipeline-status-text');

  if (pipelineBtn) {
    pipelineBtn.addEventListener('click', async () => {
      pipelineBtn.disabled = true;
      pipelineBtn.innerText = 'Streaming Pipeline...';
      if (drawer) drawer.classList.remove('hidden');
      if (stagesDiv) stagesDiv.innerHTML = '';

      try {
        await api.streamPipeline('/api/process-stream', { meeting_id: meeting.id }, {
          onEvent: (event) => {
            addPipelineEvent(event);
            if (stagesDiv) {
              const row = document.createElement('div');
              row.className = 'p-2 rounded bg-slate-950 border border-white/5 flex items-center justify-between';
              row.innerHTML = `
                <div class="flex items-center gap-2">
                  <span class="text-cyan-400">●</span>
                  <span class="text-slate-200">${escapeHtml(event.stage_name || event.agent || 'Agent')}</span>
                </div>
                <span class="text-slate-400 text-[10px]">${escapeHtml(event.message || 'Running')}</span>
              `;
              stagesDiv.appendChild(row);
              stagesDiv.scrollTop = stagesDiv.scrollHeight;
            }
            if (statusText) statusText.innerText = event.message || 'Processing...';
          },
          onError: (err) => {
            showToast(err.message || 'Pipeline stage failed', 'warning');
          },
          onComplete: (completedDossier) => {
            setState({ activeDossier: completedDossier });
            showToast('Intelligence dossier generated and verified!');
            renderContent(container, { ...meeting, dossier: completedDossier, processed: true });
          }
        });
      } catch (err) {
        showToast('Processing error: ' + err.message, 'warning');
      } finally {
        pipelineBtn.disabled = false;
        pipelineBtn.innerText = 'Re-run Intelligence Pipeline';
      }
    });
  }

  // Email action buttons
  const gmailBtn = container.querySelector('#btn-open-gmail');
  if (gmailBtn && emailDraft) {
    gmailBtn.addEventListener('click', () => {
      const url = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(emailDraft.to)}&su=${encodeURIComponent(emailDraft.subject)}&body=${encodeURIComponent(emailDraft.body)}`;
      window.open(url, '_blank');
      showToast('Opening Gmail with pre-filled follow-up draft...');
    });
  }

  const copyEmailBtn = container.querySelector('#btn-copy-email');
  if (copyEmailBtn && emailDraft) {
    copyEmailBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(emailDraft.body).then(() => {
        showToast('Follow-up email draft copied to clipboard!');
      });
    });
  }

  // Jira copy button
  const copyJiraBtn = container.querySelector('#btn-copy-jira');
  if (copyJiraBtn && jiraTickets.length > 0) {
    copyJiraBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(JSON.stringify(jiraTickets, null, 2)).then(() => {
        showToast('Jira ticket payloads copied to clipboard!');
      });
    });
  }

  // ICS download buttons
  container.querySelectorAll('.btn-ics-download').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.getAttribute('data-ics-idx'), 10);
      const evt = calendarEvents[idx];
      if (evt && evt.ics_data) {
        const blob = new Blob([evt.ics_data], { type: 'text/calendar;charset=utf-8' });
        const link = document.createElement('a');
        link.href = window.URL.createObjectURL(blob);
        link.setAttribute('download', `${evt.id || 'meeting'}.ics`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        showToast(`Downloaded ${evt.title} (.ics)`);
      }
    });
  });
}
