/**
 * router.js - Client-Side Hash Router for OmiMind 2.0
 */

import { renderHome } from './views/home.js';
import { renderAsk } from './views/ask.js';
import { renderMeetings } from './views/meetings.js';
import { renderMeetingDetail } from './views/meeting_detail.js';
import { renderMemory } from './views/memory.js';
import { renderActions } from './views/actions.js';
import { renderActivity } from './views/activity.js';
import { updateNavActive } from './components/nav.js';

export function navigate(path) {
  window.location.hash = path.startsWith('#') ? path : '#' + path;
}

export function handleRoute() {
  const hash = window.location.hash.slice(1) || 'home';
  const mainContainer = document.getElementById('main-view-container');
  if (!mainContainer) return;

  const [routePath, queryString] = hash.split('?');
  const params = new URLSearchParams(queryString || '');

  // Update navigation highlighting
  const baseRoute = routePath.split('/')[0];
  updateNavActive(baseRoute);

  // Route matching
  if (baseRoute === 'home') {
    renderHome(mainContainer);
  } else if (baseRoute === 'ask') {
    const q = params.get('q') || '';
    renderAsk(mainContainer, q);
  } else if (baseRoute === 'meetings') {
    renderMeetings(mainContainer);
  } else if (baseRoute === 'meeting') {
    const meetingId = routePath.split('/')[1] || 'q4_strategy';
    renderMeetingDetail(mainContainer, meetingId);
  } else if (baseRoute === 'memory') {
    renderMemory(mainContainer);
  } else if (baseRoute === 'actions') {
    renderActions(mainContainer);
  } else if (baseRoute === 'activity') {
    renderActivity(mainContainer);
  } else {
    renderHome(mainContainer);
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

export function initRouter() {
  window.addEventListener('hashchange', handleRoute);
  handleRoute();
}
