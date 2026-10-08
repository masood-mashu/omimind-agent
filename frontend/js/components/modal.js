/**
 * modal.js - Reusable Accessible Dialog & Slide-over Component
 * Fully keyboard-safe, focus trapped, mobile viewport aware, and WCAG AA compliant.
 */

let previouslyFocusedElement = null;
let activeKeyDownHandler = null;

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[c]);
}

export function openModal({ title, subtitle = '', contentHtml, actionsHtml = '' }) {
  closeModal();

  previouslyFocusedElement = document.activeElement;

  const backdrop = document.createElement('div');
  backdrop.id = 'omi-modal-backdrop';
  backdrop.className = 'fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4 transition-opacity';
  backdrop.setAttribute('role', 'dialog');
  backdrop.setAttribute('aria-modal', 'true');
  backdrop.setAttribute('aria-labelledby', 'omi-modal-title');

  backdrop.innerHTML = `
    <div class="omi-card omi-surface-overlay max-w-2xl w-full max-h-[85vh] max-h-[85dvh] flex flex-col shadow-2xl border border-white/15 overflow-hidden transform transition-all">
      <div class="px-5 py-3.5 sm:px-6 sm:py-4 border-b border-white/10 flex items-center justify-between flex-shrink-0">
        <div>
          <h3 id="omi-modal-title" class="text-base font-bold text-white">${escapeHtml(title)}</h3>
          ${subtitle ? `<p class="text-xs text-slate-300 mt-0.5">${escapeHtml(subtitle)}</p>` : ''}
        </div>
        <button id="omi-modal-close" class="touch-target-44 text-slate-400 hover:text-white rounded-lg hover:bg-white/5 transition flex items-center justify-center" aria-label="Close dialog">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>
      <div class="p-5 sm:p-6 overflow-y-auto space-y-4 flex-1 text-sm text-slate-200 custom-scrollbar overscroll-contain">
        ${contentHtml}
      </div>
      ${actionsHtml ? `<div class="px-5 py-3 sm:px-6 sm:py-3.5 border-t border-white/10 bg-slate-950/60 flex items-center justify-end gap-3 flex-shrink-0">${actionsHtml}</div>` : ''}
    </div>
  `;

  document.body.appendChild(backdrop);
  document.body.style.overflow = 'hidden';

  const closeBtn = document.getElementById('omi-modal-close');
  if (closeBtn) closeBtn.addEventListener('click', closeModal);

  backdrop.addEventListener('click', (e) => {
    if (e.target === backdrop) closeModal();
  });

  // Focus trap and Escape handling
  activeKeyDownHandler = (e) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      closeModal();
      return;
    }

    if (e.key === 'Tab') {
      const focusable = backdrop.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;

      const firstEl = focusable[0];
      const lastEl = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === firstEl) {
          e.preventDefault();
          lastEl.focus();
        }
      } else {
        if (document.activeElement === lastEl) {
          e.preventDefault();
          firstEl.focus();
        }
      }
    }
  };
  window.addEventListener('keydown', activeKeyDownHandler);

  // Focus initial element inside modal
  setTimeout(() => {
    const initialInput = backdrop.querySelector('input, textarea, button:not(#omi-modal-close)');
    if (initialInput) {
      initialInput.focus();
    } else if (closeBtn) {
      closeBtn.focus();
    }
  }, 50);
}

export function closeModal() {
  const existing = document.getElementById('omi-modal-backdrop');
  if (existing) {
    existing.remove();
    document.body.style.overflow = '';
  }

  if (activeKeyDownHandler) {
    window.removeEventListener('keydown', activeKeyDownHandler);
    activeKeyDownHandler = null;
  }

  if (previouslyFocusedElement && typeof previouslyFocusedElement.focus === 'function') {
    previouslyFocusedElement.focus();
    previouslyFocusedElement = null;
  }
}

