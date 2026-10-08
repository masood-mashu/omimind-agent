/**
 * nav.js - Responsive Navigation Component (Desktop Sidebar + Mobile Bottom Bar)
 */

import { navigate } from '../router.js';

export function updateNavActive(activeRoute) {
  // Desktop sidebar links
  document.querySelectorAll('[data-route]').forEach(link => {
    const route = link.getAttribute('data-route');
    const isCurrent = route === activeRoute;
    if (isCurrent) {
      link.className = "flex items-center gap-3 px-3.5 py-2.5 rounded-xl bg-cyan-500/10 text-cyan-300 font-semibold border border-cyan-500/30 text-xs transition shadow-sm shadow-cyan-500/10";
      link.setAttribute('aria-current', 'page');
    } else {
      link.className = "flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-slate-400 hover:text-white hover:bg-white/5 font-medium text-xs transition";
      link.removeAttribute('aria-current');
    }
  });

  // Mobile bottom bar links
  document.querySelectorAll('[data-mobile-route]').forEach(link => {
    const route = link.getAttribute('data-mobile-route');
    const isCurrent = route === activeRoute;
    if (isCurrent) {
      link.className = "touch-target-44 flex flex-col items-center justify-center flex-1 py-1 text-cyan-300 font-bold text-[10px]";
      link.setAttribute('aria-current', 'page');
    } else {
      link.className = "touch-target-44 flex flex-col items-center justify-center flex-1 py-1 text-slate-400 hover:text-white text-[10px]";
      link.removeAttribute('aria-current');
    }
  });
}

export function initNav() {
  document.addEventListener('click', (e) => {
    // Only intercept primary left click without modifier keys so middle click and open-in-new-tab work natively
    if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey) return;

    const routeBtn = e.target.closest('[data-route]');
    if (routeBtn) {
      e.preventDefault();
      const route = routeBtn.getAttribute('data-route');
      if (route) navigate(route);
      return;
    }

    const mobileBtn = e.target.closest('[data-mobile-route]');
    if (mobileBtn) {
      e.preventDefault();
      const route = mobileBtn.getAttribute('data-mobile-route');
      if (route) navigate(route);
      return;
    }
  });
}

