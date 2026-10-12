import { authorizedFetch } from '../api.js';
import { signOut } from '../supabase.js';

export function renderAccount(container) {
  container.innerHTML = `<div class="mx-auto max-w-3xl space-y-6"><div><p class="text-xs font-mono-tech uppercase tracking-widest text-cyan-300">Workspace settings</p><h1 class="mt-2 text-3xl font-bold">Account</h1><p class="mt-2 text-sm text-slate-400">Your meetings, memories, agent traces, action items, and Omi connections belong to this account.</p></div><section class="rounded-2xl border border-white/10 bg-white/[.03] p-5"><h2 class="font-semibold">Delete account data</h2><p class="mt-2 text-sm leading-6 text-slate-400">This removes your Qdrant memories, Postgres workspace rows, Omi mappings, and agent run history. The action cannot be undone.</p><button id="delete-account" class="mt-4 rounded-xl border border-rose-400/40 px-4 py-2 text-xs font-bold text-rose-200">Delete my account</button></section></div>`;
  document.getElementById('delete-account')?.addEventListener('click', async () => {
    if (!window.confirm('Delete your OMIMIND account and all workspace data?')) return;
    const response = await authorizedFetch('/api/account', { method: 'DELETE' });
    if (!response.ok) throw new Error('Account deletion failed.');
    await signOut();
    window.location.hash = '#home';
    window.location.reload();
  });
}
