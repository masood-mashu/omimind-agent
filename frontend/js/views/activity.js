/**
 * activity.js - AI Activity & Multi-Agent Swarm Showcase
 * Two-layer design:
 * Layer 1: Human-readable AI workflow translating actual pipeline events into plain language.
 * Layer 2: Developer telemetry (collapsed by default) with raw SSE events and system diagnostics.
 */

import { getState } from '../state.js';
import * as api from '../api.js';

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[c]);
}

function formatHumanNarrative(event) {
  const agent = (event.agent || event.stage_name || '').toLowerCase();
  const msg = event.message || '';

  if (agent.includes('ingest') || msg.toLowerCase().includes('ingest')) {
    return {
      title: 'Captured & Ingested Speech',
      desc: msg || 'Utterances received from ambient audio stream',
      icon: '🎙',
      badge: 'Omi Ambient Voice',
      badgeColor: 'text-cyan-300 bg-cyan-950/60 border-cyan-500/30'
    };
  }
  if (agent.includes('storage') || agent.includes('vector') || agent.includes('qdrant') || msg.toLowerCase().includes('qdrant') || msg.toLowerCase().includes('vector')) {
    return {
      title: 'Stored in Qdrant Semantic Memory',
      desc: msg || 'Indexed 384-dimensional dense vectors into omi_ambient_memory collection',
      icon: '🧠',
      badge: 'Qdrant Cloud',
      badgeColor: 'text-indigo-300 bg-indigo-950/60 border-indigo-500/30'
    };
  }
  if (agent.includes('analyst') || msg.toLowerCase().includes('analyst') || msg.toLowerCase().includes('summary')) {
    return {
      title: 'Meeting Analyst Synthesized Session',
      desc: msg || 'Generated executive takeaways, confirmed decisions, and identified project risks',
      icon: '📋',
      badge: 'Meeting Analyst (6ac577cccf263d0b068d001a)',
      badgeColor: 'text-sky-300 bg-sky-950/60 border-sky-500/30'
    };
  }
  if (agent.includes('action') || msg.toLowerCase().includes('action') || msg.toLowerCase().includes('commitment')) {
    return {
      title: 'Action Extractor Identified Commitments',
      desc: msg || 'Extracted concrete deliverables, assignees, deadlines, and direct quotes',
      icon: '⚡',
      badge: 'Action Extractor (6ac578bf4b079480ed4ea5a5)',
      badgeColor: 'text-amber-300 bg-amber-950/60 border-amber-500/30'
    };
  }
  if (agent.includes('recall') || msg.toLowerCase().includes('recall')) {
    return {
      title: 'Recall Agent Grounded Response',
      desc: msg || 'Retrieved ambient memory vectors and synthesized grounded answer',
      icon: '🔍',
      badge: 'Recall Agent (6ac2646b367124ed07f49bdd)',
      badgeColor: 'text-purple-300 bg-purple-950/60 border-purple-500/30'
    };
  }
  if (agent.includes('validat') || agent.includes('normaliz') || msg.toLowerCase().includes('validat')) {
    return {
      title: 'Deterministic Normalization Verified',
      desc: msg || 'Validated calendar schemas and confirmed zero ungrounded action items',
      icon: '✓',
      badge: 'Schema Verification',
      badgeColor: 'text-emerald-300 bg-emerald-950/60 border-emerald-500/30'
    };
  }
  if (agent.includes('manager') || msg.toLowerCase().includes('manager')) {
    return {
      title: 'Lyzr Manager Routed Reasoning',
      desc: msg || 'Hierarchical orchestrator evaluated task context and delegated to specialized agent swarm',
      icon: '🤖',
      badge: 'Manager Agent (6ac5795151dce5f00e746950)',
      badgeColor: 'text-purple-300 bg-purple-950/60 border-purple-500/30'
    };
  }
  return {
    title: event.stage_name || event.agent || 'Pipeline Execution Step',
    desc: msg || 'Multi-agent event processed',
    icon: '●',
    badge: 'System Event',
    badgeColor: 'text-slate-300 bg-slate-900 border-white/10'
  };
}

export function renderActivity(container) {
  const state = getState();
  const health = state.health || {};
  const stats = health.qdrant_stats || {};
  const pointsCount = stats.points_count ?? 'Active';
  const lyzrStatus = health.lyzr_status || {};
  const events = state.pipelineEvents || [];

  container.innerHTML = `
    <div class="view-container max-w-5xl mx-auto space-y-8 py-4 px-4 sm:px-6">
      
      <!-- Top Title -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-4">
        <div>
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-mono-tech mb-2">
            <span>● Multi-Agent Swarm Observability</span>
          </div>
          <h1 class="text-xl sm:text-2xl font-bold text-white flex items-center gap-2.5">
            <span>🤖</span>
            <span>AI Activity & Swarm Execution</span>
          </h1>
          <p class="text-xs sm:text-sm text-slate-300 mt-0.5">
            Real-time trace of Omi audio ingestion, Qdrant vector memory, and Lyzr Manager hierarchical agent delegation.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <span class="px-3 py-1.5 rounded-xl bg-slate-900 border border-white/10 text-xs font-mono-tech text-emerald-400">
            Provider: Lyzr Studio Cloud
          </span>
        </div>
      </div>

      <!-- LAYER 1: Human-Readable AI Workflow & Real Topology -->
      <section class="space-y-6">
        
        <!-- Live Workflow Narrative (if session has streamed events) -->
        <div class="omi-card p-6 border border-white/10 bg-[#0e131f] space-y-4">
          <div class="flex items-center justify-between border-b border-white/5 pb-3">
            <div class="flex items-center gap-2">
              <span class="text-emerald-400 font-bold">✦</span>
              <h2 class="text-base font-bold text-white">Live AI Execution Narrative</h2>
            </div>
            <span class="text-xs font-mono-tech text-slate-400">
              ${events.length} session event${events.length === 1 ? '' : 's'} recorded
            </span>
          </div>

          <div class="space-y-3">
            ${events.length > 0 ? events.map(e => {
              const narrative = formatHumanNarrative(e);
              return `
                <div class="p-4 rounded-xl bg-slate-950/60 border border-white/5 flex items-start gap-3.5 hover:border-white/10 transition">
                  <span class="w-8 h-8 rounded-lg bg-slate-900 text-slate-200 border border-white/10 flex items-center justify-center text-sm flex-shrink-0 mt-0.5">
                    ${narrative.icon}
                  </span>
                  <div class="flex-1 space-y-1">
                    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                      <span class="font-bold text-xs sm:text-sm text-white">${escapeHtml(narrative.title)}</span>
                      <span class="px-2 py-0.5 rounded text-[10px] font-mono-tech border self-start sm:self-auto ${narrative.badgeColor}">
                        ${escapeHtml(narrative.badge)}
                      </span>
                    </div>
                    <p class="text-xs text-slate-300 font-sans leading-relaxed">
                      ${escapeHtml(narrative.desc)}
                    </p>
                  </div>
                </div>
              `;
            }).join('') : `
              <div class="p-6 text-center text-slate-300 text-xs space-y-2 border border-dashed border-white/10 rounded-xl">
                <p class="text-white font-medium">No live stream events recorded in this session yet.</p>
                <p class="text-slate-400 max-w-md mx-auto">
                  When you speak into the mic on <a href="#home" class="text-cyan-400 hover:underline">Home</a> or run an intelligence pipeline on <a href="#meetings" class="text-cyan-400 hover:underline">Meetings</a>, real agent reasoning steps stream here in real time.
                </p>
              </div>
            `}
          </div>
        </div>

        <!-- Configured Lyzr Manager Architecture -->
        <div class="omi-card p-6 border border-white/10 bg-[#0e131f] space-y-5">
          <div class="flex items-center justify-between border-b border-white/5 pb-3">
            <div>
              <h2 class="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono-tech">
                Configured Lyzr Manager Architecture
              </h2>
              <p class="text-xs text-slate-300 mt-0.5">Manager agent invocation (delegation depends on Lyzr Studio configuration)</p>
            </div>
            <span class="text-xs font-mono-tech px-2.5 py-1 rounded-lg bg-purple-900/40 text-purple-300 border border-purple-500/30">
              Lyzr Manager: 6ac5795151dce5f00e746950
            </span>
          </div>

          <div class="space-y-4">
            
            <!-- Step 1: Omi Audio Ingestion -->
            <div class="p-4 rounded-xl bg-slate-950/70 border border-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div class="flex items-center gap-3">
                <span class="w-8 h-8 rounded-lg bg-cyan-500/20 text-cyan-300 flex items-center justify-center text-sm font-bold font-mono-tech">1</span>
                <div>
                  <h3 class="font-bold text-sm text-white">Omi Ambient Audio Stream</h3>
                  <p class="text-xs text-slate-300">Continuous speech capture via Omi Webhook & Live Web Audio API</p>
                </div>
              </div>
              <span class="text-[11px] font-mono-tech px-2.5 py-1 rounded-lg bg-cyan-900/30 text-cyan-300 border border-cyan-500/30">
                Webhook: /api/omi-webhook
              </span>
            </div>

            <div class="flex justify-center -my-2 text-slate-500">↓</div>

            <!-- Step 2: Qdrant Semantic Memory -->
            <div class="p-4 rounded-xl bg-slate-950/70 border border-indigo-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div class="flex items-center gap-3">
                <span class="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-300 flex items-center justify-center text-sm font-bold font-mono-tech">2</span>
                <div>
                  <h3 class="font-bold text-sm text-white">Qdrant Semantic Memory</h3>
                  <p class="text-xs text-slate-300">Persistent collection <code class="text-indigo-300 font-mono-tech">omi_ambient_memory</code> · Cosine Distance</p>
                </div>
              </div>
              <div class="text-[11px] font-mono-tech text-right">
                <span class="text-indigo-300 font-bold block">${pointsCount} Vectors Stored</span>
                <span class="text-slate-400 text-[10px]">384-dim dense embeddings</span>
              </div>
            </div>

            <div class="flex justify-center -my-2 text-slate-500">↓</div>

            <!-- Step 3: Lyzr Manager & Specialized Agents -->
            <div class="p-5 rounded-xl bg-slate-950/90 border border-purple-500/40 space-y-4">
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div class="flex items-center gap-3">
                  <span class="w-8 h-8 rounded-lg bg-purple-500/20 text-purple-300 flex items-center justify-center text-sm font-bold font-mono-tech">3</span>
                  <div>
                    <h3 class="font-bold text-sm text-white">Configured Lyzr Manager Coordinator</h3>
                    <p class="text-xs text-slate-300">Supervisory reasoning & task orchestration</p>
                  </div>
                </div>
                <span class="text-[11px] font-mono-tech px-2.5 py-1 rounded-lg bg-purple-900/40 text-purple-300 border border-purple-500/30">
                  Manager: 6ac5795151dce5f00e746950
                </span>
              </div>

              <!-- 3 Real Specialized Child Agents -->
              <div class="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 border-t border-white/5">
                
                <!-- Agent 3a: Recall Agent -->
                <div class="p-3.5 rounded-lg bg-slate-900/80 border border-white/5 space-y-1">
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-xs text-cyan-300">Recall Agent</span>
                    <span class="text-[9px] font-mono-tech px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400">ACTIVE</span>
                  </div>
                  <p class="text-[11px] text-slate-300 leading-snug">
                    Grounds conversational queries against raw Qdrant ambient memories.
                  </p>
                  <div class="text-[10px] text-slate-400 font-mono-tech pt-1">
                    Agent ID: 6ac2646b367124ed07f49bdd
                  </div>
                </div>

                <!-- Agent 3b: Meeting Analyst -->
                <div class="p-3.5 rounded-lg bg-slate-900/80 border border-white/5 space-y-1">
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-xs text-indigo-300">Meeting Analyst</span>
                    <span class="text-[9px] font-mono-tech px-1.5 py-0.5 rounded bg-indigo-950 text-indigo-400">ACTIVE</span>
                  </div>
                  <p class="text-[11px] text-slate-300 leading-snug">
                    Synthesizes key decisions, duration, and unresolved project risks.
                  </p>
                  <div class="text-[10px] text-slate-400 font-mono-tech pt-1">
                    Agent ID: 6ac577cccf263d0b068d001a
                  </div>
                </div>

                <!-- Agent 3c: Action Extractor -->
                <div class="p-3.5 rounded-lg bg-slate-900/80 border border-white/5 space-y-1">
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-xs text-amber-300">Action Extractor</span>
                    <span class="text-[9px] font-mono-tech px-1.5 py-0.5 rounded bg-amber-950 text-amber-400">ACTIVE</span>
                  </div>
                  <p class="text-[11px] text-slate-300 leading-snug">
                    Extracts verbal commitments, assignees, deadlines, and direct quotes.
                  </p>
                  <div class="text-[10px] text-slate-400 font-mono-tech pt-1">
                    Agent ID: 6ac578bf4b079480ed4ea5a5
                  </div>
                </div>

              </div>
            </div>

            <div class="flex justify-center -my-2 text-slate-500">↓</div>

            <!-- Step 4: Deterministic Normalization -->
            <div class="p-4 rounded-xl bg-slate-950/70 border border-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div class="flex items-center gap-3">
                <span class="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-300 flex items-center justify-center text-sm font-bold font-mono-tech">4</span>
                <div>
                  <h3 class="font-bold text-sm text-white">Deterministic Normalization & Validation</h3>
                  <p class="text-xs text-slate-300">Guarantees zero hallucinated actions and enforces strict RFC 5545 calendar schemas</p>
                </div>
              </div>
              <span class="text-[11px] font-mono-tech text-emerald-300">Verified Output</span>
            </div>

            <div class="flex justify-center -my-2 text-slate-500">↓</div>

            <!-- Step 5: User-controlled outputs -->
            <div class="p-4 rounded-xl bg-slate-950/70 border border-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div class="flex items-center gap-3">
                <span class="w-8 h-8 rounded-lg bg-blue-500/20 text-blue-300 flex items-center justify-center text-sm font-bold font-mono-tech">5</span>
                <div>
                  <h3 class="font-bold text-sm text-white">User-Controlled Outputs</h3>
                  <p class="text-xs text-slate-300">Follow-up email drafts, Jira ticket payloads, Google Meet & iCal sync</p>
                </div>
              </div>
              <span class="text-[11px] font-mono-tech text-blue-300">Zero Autonomous Side Effects</span>
            </div>

          </div>
        </div>

      </section>

      <!-- LAYER 2: Developer Telemetry (Collapsed by Default) -->
      <section class="omi-card border border-white/10 bg-[#0e131f] overflow-hidden">
        <details class="group" aria-label="Developer Telemetry">
          <summary class="p-5 cursor-pointer flex items-center justify-between text-xs font-mono-tech text-slate-300 hover:text-white select-none transition">
            <span class="flex items-center gap-2">
              <svg class="w-4 h-4 transition-transform group-open:rotate-90 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
              <span class="font-bold text-white">Developer Telemetry & Diagnostics</span>
              <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px]">Advanced</span>
            </span>
            <span class="text-[11px] text-slate-400">Click to expand raw SSE logs & endpoints</span>
          </summary>

          <div class="p-5 pt-0 space-y-6 border-t border-white/5">
            
            <!-- Raw SSE Stream Console -->
            <div class="space-y-2 pt-4">
              <h3 class="text-[11px] font-bold text-slate-300 font-mono-tech uppercase tracking-wider">
                Raw Event Log (${events.length} Events)
              </h3>
              <div id="activity-events-console" class="p-4 rounded-xl bg-slate-950 font-mono-tech text-xs space-y-2 max-h-72 overflow-y-auto border border-white/5 custom-scrollbar">
                ${events.length > 0 ? events.map(e => `
                  <div class="flex items-start gap-2.5 text-[11px]">
                    <span class="text-cyan-400 flex-shrink-0">›</span>
                    <span class="text-indigo-300 font-bold">[${escapeHtml(e.agent || e.stage_name || 'System')}]:</span>
                    <span class="text-slate-300 break-all">${escapeHtml(e.message || JSON.stringify(e))}</span>
                  </div>
                `).join('') : `
                  <div class="text-slate-400 text-center py-4 text-[11px]">
                    No raw events stream captured yet. Run a meeting pipeline to view real-time SSE stream frames.
                  </div>
                `}
              </div>
            </div>

            <!-- System Diagnostics & Cloud Endpoints -->
            <div class="space-y-2">
              <h3 class="text-[11px] font-bold text-slate-300 font-mono-tech uppercase tracking-wider">
                Backend System Diagnostics
              </h3>
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono-tech">
                <div class="p-3.5 rounded-xl bg-slate-950 border border-white/5 space-y-1">
                  <span class="text-slate-400 text-[10px] block">EMBEDDING ENGINE</span>
                  <span class="text-cyan-300 font-bold block">${escapeHtml(health.embedding_provider || 'FastEmbed')}</span>
                  <span class="text-slate-400 text-[10px]">Dimension: ${health.vector_dimension || 384}</span>
                </div>
                <div class="p-3.5 rounded-xl bg-slate-950 border border-white/5 space-y-1">
                  <span class="text-slate-400 text-[10px] block">QDRANT CLUSTER</span>
                  <span class="text-indigo-300 font-bold block">${escapeHtml(health.qdrant_persistence_mode || 'Cloud')}</span>
                  <span class="text-slate-400 text-[10px]">Points: ${pointsCount}</span>
                </div>
                <div class="p-3.5 rounded-xl bg-slate-950 border border-white/5 space-y-1">
                  <span class="text-slate-400 text-[10px] block">LYZR MULTI-AGENT SWARM</span>
                  <span class="text-purple-300 font-bold block">${lyzrStatus.configured ? 'Studio Cloud Active' : 'Unconfigured'}</span>
                  <span class="text-slate-400 text-[10px]">Timeout: 45s</span>
                </div>
              </div>
            </div>

          </div>
        </details>
      </section>

    </div>
  `;
}

