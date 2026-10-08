/**
 * ask.js - Ask OmiMind Hero Conversational Memory Assistant
 * Real natural language recall powered by Qdrant semantic memory & Lyzr Manager/Recall Agent.
 */

import { getState, addAskMessage } from '../state.js';
import * as api from '../api.js';
import { showToast } from '../components/toast.js';

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[c]);
}

export function renderAsk(container, initialQuery = '') {
  const state = getState();

  container.innerHTML = `
    <div class="view-container max-w-4xl mx-auto space-y-6 py-4 px-4 sm:px-6">
      
      <!-- Top Title & Description -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/5 pb-4">
        <div>
          <h1 class="text-xl sm:text-2xl font-bold text-white flex items-center gap-2.5">
            <span class="text-cyan-400">✦</span>
            <span>Ask OmiMind</span>
          </h1>
          <p class="text-xs sm:text-sm text-slate-300 mt-0.5">
            Grounded conversational recall over your ambient conversations and meetings.
          </p>
        </div>
        <div class="flex items-center gap-2 text-xs">
          <span class="px-2.5 py-1 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-mono-tech text-[11px]">
            Lyzr Recall Agent • Qdrant Grounding
          </span>
        </div>
      </div>

      <!-- Conversational Stream Timeline -->
      <div id="ask-timeline" class="space-y-6 min-h-[340px]" role="region" aria-live="polite" aria-label="Conversation History">
        ${renderTimeline(state.askHistory)}
      </div>

      <!-- Loading State Container -->
      <div id="ask-loading" class="hidden omi-card p-4 space-y-2 border border-cyan-500/30 bg-[#0e131f] shadow-lg" role="status" aria-live="assertive">
        <div class="flex items-center gap-3 text-xs text-cyan-300 font-medium">
          <span class="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping"></span>
          <span id="ask-loading-text">Searching your memories in Qdrant...</span>
        </div>
        <div class="w-full bg-slate-800 rounded-full h-1 overflow-hidden">
          <div id="ask-loading-bar" class="bg-gradient-to-r from-cyan-500 to-indigo-500 h-1 w-1/3 animate-pulse"></div>
        </div>
      </div>

      <!-- Sticky Command Surface Input Bar -->
      <div class="sticky bottom-4 z-20">
        <form id="ask-form" class="relative group">
          <div class="absolute -inset-0.5 bg-gradient-to-r from-cyan-500 to-indigo-600 rounded-2xl blur opacity-25 group-hover:opacity-40 transition"></div>
          <div class="relative flex items-center bg-[#0e131f] border border-white/15 rounded-2xl p-2 shadow-2xl">
            <div class="pl-2.5 text-cyan-400 flex items-center flex-shrink-0">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg>
            </div>
            
            <textarea 
              id="ask-input" 
              rows="1" 
              placeholder="Ask anything you've heard... (Press Enter to ask, Shift+Enter for newline)"
              class="w-full bg-transparent border-none py-2.5 px-3 text-sm text-white placeholder-slate-400 focus:outline-none resize-none max-h-32"
              autocomplete="off"
            >${escapeHtml(initialQuery)}</textarea>

            <div class="flex items-center gap-1.5 flex-shrink-0">
              <button 
                type="button" 
                id="ask-voice-toggle-btn"
                class="touch-target-44 p-2 rounded-xl text-slate-400 hover:text-cyan-300 hover:bg-slate-800/80 transition"
                title="Speak voice question"
                aria-label="Voice question input"
              >
                <svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z"/></svg>
              </button>

              <button 
                type="submit" 
                id="ask-submit-btn"
                class="touch-target-44 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs sm:text-sm shadow-md transition flex items-center gap-1.5"
              >
                <span>Ask</span>
                <svg class="w-4 h-4 ml-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
              </button>
            </div>
          </div>
        </form>

        <!-- Suggested Follow-ups & Query History Hydration Rail -->
        <div class="omi-filter-rail mt-2.5 px-1 items-center">
          <span class="text-slate-400 text-[11px] font-medium flex-shrink-0">Suggestions:</span>
          <button type="button" class="ask-suggest-chip touch-target-44 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 transition text-xs whitespace-nowrap" data-query="What did I say about Project Nebula?">
            "What did I say about Project Nebula?"
          </button>
          <button type="button" class="ask-suggest-chip touch-target-44 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 transition text-xs whitespace-nowrap" data-query="What did Sarah say about the budget?">
            "What did Sarah say about the budget?"
          </button>
          <button type="button" class="ask-suggest-chip touch-target-44 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 transition text-xs whitespace-nowrap" data-query="What were the critical action items?">
            "What were the critical action items?"
          </button>
        </div>
      </div>

    </div>
  `;

  // Attach handlers
  const form = container.querySelector('#ask-form');
  const input = container.querySelector('#ask-input');
  const loadingEl = container.querySelector('#ask-loading');
  const loadingText = container.querySelector('#ask-loading-text');
  const voiceBtn = container.querySelector('#ask-voice-toggle-btn');

  // Auto-expanding textarea height
  if (input) {
    const adjustHeight = () => {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 128) + 'px';
    };
    input.addEventListener('input', adjustHeight);
    adjustHeight();

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        executeAsk(input.value);
      }
    });
  }

  if (voiceBtn) {
    voiceBtn.addEventListener('click', () => {
      const homeMic = document.getElementById('btn-top-mic');
      if (homeMic) homeMic.click();
    });
  }

  async function executeAsk(question) {
    if (!question || !question.trim()) return;
    const cleanQ = question.trim();
    if (input) {
      input.value = '';
      input.style.height = 'auto';
    }

    // P1 Requirement 16: Hydrate cached state if query was already answered
    const existingIndex = state.askHistory.findIndex(
      h => h.question.toLowerCase().trim() === cleanQ.toLowerCase()
    );
    if (existingIndex !== -1) {
      const cached = state.askHistory[existingIndex];
      // Move to top of current recency
      state.askHistory.splice(existingIndex, 1);
      state.askHistory.push(cached);
      showToast('Hydrated query from session cache');
      renderAsk(container);
      return;
    }

    if (loadingEl) {
      loadingEl.classList.remove('hidden');
      if (loadingText) loadingText.innerText = 'Searching your memories in Qdrant...';
    }

    try {
      if (loadingText) {
        setTimeout(() => {
          if (loadingText) loadingText.innerText = 'Finding relevant conversations & speakers...';
        }, 500);
        setTimeout(() => {
          if (loadingText) loadingText.innerText = 'Grounding response via Lyzr Manager & Recall Agent...';
        }, 1200);
      }

      const res = await api.askMemory(cleanQ, 5);

      const entry = {
        id: 'ask_' + Date.now(),
        question: cleanQ,
        answer: res.answer || 'No direct conversational records found in Qdrant.',
        source: res.source || 'lyzr_studio_cloud',
        agent_id: res.agent_id || '6ac2646b367124ed07f49bdd',
        matches: res.matches || [],
        relevance_top: res.relevance_top || 0.0,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      addAskMessage(entry);
      renderAsk(container);
    } catch (err) {
      console.error('Ask failed:', err);
      showToast('Error recalling memory: ' + err.message, 'warning');
      // Fallback to direct queryMemory if Lyzr agent encountered temporary network glitch
      try {
        const fallbackRes = await api.queryMemory(cleanQ, 4);
        const entry = {
          id: 'ask_' + Date.now(),
          question: cleanQ,
          answer: fallbackRes.answer || 'No memory match found.',
          source: 'qdrant_vector_memory',
          agent_id: 'qdrant_recall',
          matches: fallbackRes.matches || [],
          relevance_top: fallbackRes.relevance_top || 0.0,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        addAskMessage(entry);
        renderAsk(container);
      } catch (_) {}
    } finally {
      if (loadingEl) loadingEl.classList.add('hidden');
    }
  }

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      if (input) executeAsk(input.value);
    });
  }

  container.querySelectorAll('.ask-suggest-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      const q = btn.getAttribute('data-query');
      if (q) executeAsk(q);
    });
  });

  // If initial query provided via URL param, run it automatically
  if (initialQuery && initialQuery.trim()) {
    executeAsk(initialQuery.trim());
  }
}

function renderTimeline(history) {
  if (!history || history.length === 0) {
    return `
      <div class="omi-card p-10 text-center space-y-4 border-dashed border-white/10">
        <div class="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center mx-auto text-xl">
          💭
        </div>
        <div>
          <h2 class="text-base font-semibold text-white">Ask your ambient memory anything</h2>
          <p class="text-xs text-slate-300 mt-1 max-w-md mx-auto">
            OmiMind continuously indexes utterances into Qdrant. Ask natural questions to recall what was said, who said it, and when.
          </p>
        </div>
        <div class="pt-2 flex flex-wrap justify-center gap-2">
          <button type="button" class="ask-suggest-chip touch-target-44 px-3 py-1.5 rounded-xl bg-slate-900 border border-white/10 text-xs text-slate-200 hover:text-white hover:border-cyan-500/40 transition" data-query="What did I say about Project Nebula?">
            "What did I say about Project Nebula?"
          </button>
          <button type="button" class="ask-suggest-chip touch-target-44 px-3 py-1.5 rounded-xl bg-slate-900 border border-white/10 text-xs text-slate-200 hover:text-white hover:border-cyan-500/40 transition" data-query="What did Sarah say about the budget?">
            "What did Sarah say about the budget?"
          </button>
        </div>
      </div>
    `;
  }

  return history.map((item, idx) => `
    <div class="space-y-3">
      
      <!-- User Query Bubble -->
      <div class="flex justify-end">
        <div class="max-w-[85%] rounded-2xl rounded-tr-sm bg-gradient-to-r from-blue-600 to-indigo-600 p-4 text-white shadow-lg text-sm">
          <p class="font-medium">${escapeHtml(item.question)}</p>
          <span class="text-[10px] text-blue-200 mt-1 block text-right font-mono-tech">${escapeHtml(item.timestamp || '')}</span>
        </div>
      </div>

      <!-- OmiMind Answer Card -->
      <div class="flex justify-start">
        <div class="omi-card max-w-[95%] sm:max-w-[90%] p-5 space-y-4 border border-white/10 shadow-xl bg-[#0e131f]">
          
          <!-- Answer Header & Grounding Badge -->
          <div class="flex items-center justify-between border-b border-white/5 pb-2.5">
            <div class="flex items-center gap-2">
              <span class="w-6 h-6 rounded-lg bg-cyan-500/20 text-cyan-300 flex items-center justify-center text-xs font-bold font-mono-tech">
                Ω
              </span>
              <span class="font-bold text-xs text-white">OmiMind Answer</span>
            </div>
            
            <!-- Grounding Indicator (honest values from backend) -->
            <div class="flex items-center gap-2">
              ${item.matches && item.matches.length > 0 ? `
                <span class="px-2.5 py-0.5 rounded-full text-[10px] font-mono-tech bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  Grounded in ${item.matches.length} memor${item.matches.length === 1 ? 'y' : 'ies'} · Top relevance: ${Number(item.relevance_top).toFixed(2)}
                </span>
              ` : `
                <span class="px-2.5 py-0.5 rounded-full text-[10px] font-mono-tech bg-slate-800 text-slate-300 border border-white/10">
                  Direct match
                </span>
              `}
            </div>
          </div>

          <!-- Answer Body -->
          <div class="text-sm text-slate-100 leading-relaxed space-y-2">
            ${formatAnswerText(item.answer)}
          </div>

          <!-- Supporting Memories Accordion -->
          ${item.matches && item.matches.length > 0 ? `
            <div class="pt-2 border-t border-white/5">
              <details class="group" aria-label="Supporting Memories">
                <summary class="cursor-pointer text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center justify-between py-1 select-none">
                  <span class="flex items-center gap-1.5">
                    <svg class="w-3.5 h-3.5 transition-transform group-open:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                    <span>View ${item.matches.length} Supporting Ambient Memor${item.matches.length === 1 ? 'y' : 'ies'}</span>
                  </span>
                  <span class="text-[11px] text-slate-400 font-mono-tech">Source: Qdrant Vector DB</span>
                </summary>
                
                <div class="mt-3 space-y-2.5 pl-2 border-l-2 border-cyan-500/30">
                  ${item.matches.map((m, mIdx) => `
                    <div class="p-3 rounded-xl bg-slate-950/70 border border-white/5 space-y-1.5 text-xs">
                      <div class="flex items-center justify-between text-[11px]">
                        <div class="flex items-center gap-2">
                          <span class="font-semibold text-cyan-300 font-mono-tech">${escapeHtml(m.speaker || 'Speaker')}</span>
                          ${m.timestamp_str ? `<span class="text-slate-400 font-mono-tech text-[10px]">@ ${escapeHtml(m.timestamp_str)}</span>` : ''}
                        </div>
                        <span class="px-2 py-0.5 rounded bg-cyan-900/40 text-cyan-300 font-mono-tech text-[10px]">
                          Relevance: ${m.score !== undefined ? Number(m.score).toFixed(2) : '1.00'}
                        </span>
                      </div>
                      <p class="text-slate-200 italic font-sans leading-relaxed">
                        "${escapeHtml(m.text)}"
                      </p>
                      ${m.session_id ? `
                        <div class="text-[10px] text-slate-400 font-mono-tech">
                          Session: ${escapeHtml(m.session_id)}
                        </div>
                      ` : ''}
                    </div>
                  `).join('')}
                </div>
              </details>
            </div>
          ` : ''}

        </div>
      </div>

    </div>
  `).join('');
}

function formatAnswerText(text) {
  if (!text) return '<p class="text-slate-400">No response.</p>';
  return text.split('\n\n').map(paragraph => {
    return `<p class="leading-relaxed">${escapeHtml(paragraph)}</p>`;
  }).join('');
}

