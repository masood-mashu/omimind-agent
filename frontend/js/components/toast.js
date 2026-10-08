/**
 * toast.js - Accessible Toast Notification Component
 */

export function showToast(message, type = 'success', duration = 3200) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none max-w-sm w-full px-4';
    container.setAttribute('aria-live', 'polite');
    container.setAttribute('aria-atomic', 'true');
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.setAttribute('role', 'status');

  const colorStyles = {
    success: 'border-emerald-500/40 text-emerald-200 bg-slate-900/95 shadow-emerald-500/10',
    cyan: 'border-cyan-500/40 text-cyan-200 bg-slate-900/95 shadow-cyan-500/10',
    warning: 'border-amber-500/40 text-amber-200 bg-slate-900/95 shadow-amber-500/10',
    error: 'border-rose-500/40 text-rose-200 bg-slate-900/95 shadow-rose-500/10',
    info: 'border-indigo-500/40 text-indigo-200 bg-slate-900/95 shadow-indigo-500/10',
  };

  const dotColors = {
    success: 'bg-emerald-400',
    cyan: 'bg-cyan-400',
    warning: 'bg-amber-400',
    error: 'bg-rose-400',
    info: 'bg-indigo-400',
  };

  const chosenStyle = colorStyles[type] || colorStyles.success;
  const chosenDot = dotColors[type] || dotColors.success;

  toast.className = `toast-entry pointer-events-auto px-4 py-3 rounded-xl border ${chosenStyle} text-xs shadow-2xl flex items-center gap-3 backdrop-blur-md`;

  const dot = document.createElement('span');
  dot.className = `w-2 h-2 rounded-full ${chosenDot} flex-shrink-0 animate-pulse`;

  const textSpan = document.createElement('span');
  textSpan.className = 'flex-1 leading-snug';
  textSpan.textContent = message;

  toast.appendChild(dot);
  toast.appendChild(textSpan);
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.remove('toast-entry');
    toast.classList.add('toast-exit');
    setTimeout(() => toast.remove(), 250);
  }, duration);
}
