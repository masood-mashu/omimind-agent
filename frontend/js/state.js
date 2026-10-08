/**
 * state.js - Reactive State Management Store for OmiMind 2.0
 */

const state = {
  health: null,
  meetings: [],
  activeMeetingId: 'q4_strategy',
  activeDossier: null,
  memories: [],
  actions: [],
  askHistory: [],
  pipelineEvents: [],
  pipelineActive: false,
  isRecording: false,
  activeTab: 'summary', // For meeting detail
};

const listeners = new Set();

export function getState() {
  return state;
}

export function setState(partial) {
  Object.assign(state, partial);
  notify();
}

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function notify() {
  for (const listener of listeners) {
    try {
      listener(state);
    } catch (e) {
      console.error('State listener error:', e);
    }
  }
}

export function addAskMessage(entry) {
  state.askHistory.unshift(entry);
  notify();
}

export function addPipelineEvent(event) {
  state.pipelineEvents.push(event);
  notify();
}

export function clearPipelineEvents() {
  state.pipelineEvents = [];
  notify();
}
