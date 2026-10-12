import { authorizedFetch } from '../api.js';

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
}

export async function renderOmi(container) {
  container.innerHTML = `<div class="mx-auto max-w-4xl space-y-6"><div><p class="text-xs font-mono-tech uppercase tracking-widest text-cyan-300">Workspace connection</p><h1 class="mt-2 text-3xl font-bold">Connect Omi</h1><p class="mt-2 text-sm text-slate-400">Pair an Omi device with this account. The Omi account remains separate; this connection links its events to your OMIMIND workspace.</p></div><section class="rounded-2xl border border-white/10 bg-white/[.03] p-5"><div class="flex flex-wrap items-center justify-between gap-3"><div><h2 class="font-semibold">One-time pairing</h2><p class="mt-1 text-xs text-slate-400">Start a code, enter it in the Omi setup flow, then keep the generated webhook paths private.</p></div><button id="omi-start-pair" class="rounded-xl bg-cyan-500 px-4 py-2 text-xs font-bold text-slate-950">Start pairing</button></div><div id="omi-pair-output" class="mt-4 hidden rounded-xl border border-cyan-400/20 bg-cyan-400/5 p-4 text-sm"></div></section><section class="rounded-2xl border border-white/10 bg-white/[.03] p-5"><h2 class="font-semibold">Paired devices</h2><div id="omi-connections" class="mt-4 space-y-3"><p class="text-sm text-slate-500">Loading connections…</p></div></section></div>`;

  const output = document.getElementById('omi-pair-output');
  const load = async () => {
    const response = await authorizedFetch('/api/omi/connections');
    const data = await response.json();
    const target = document.getElementById('omi-connections');
    if (!data.connections?.length) { target.innerHTML = '<p class="text-sm text-slate-500">No Omi connection yet.</p>'; return; }
    target.innerHTML = data.connections.map((item) => `<div class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 p-4"><div><p class="text-sm font-semibold">${escapeHtml(item.device_label || 'Omi device')}</p><p class="text-xs text-slate-400">${escapeHtml(item.omi_user_id || 'Pairing pending')} · <span class="text-emerald-300">${escapeHtml(item.status)}</span></p></div><div class="flex gap-2"><button data-rotate="${escapeHtml(item.id)}" class="rounded-lg border border-amber-400/30 px-3 py-2 text-xs text-amber-200">Rotate token</button><button data-delete="${escapeHtml(item.id)}" class="rounded-lg border border-rose-400/30 px-3 py-2 text-xs text-rose-200">Revoke</button></div></div>`).join('');
  };
  document.getElementById('omi-start-pair')?.addEventListener('click', async () => {
    const response = await authorizedFetch('/api/omi/connections/pair/start', { method: 'POST' });
    const pair = await response.json();
    output.classList.remove('hidden');
    output.innerHTML = `<p class="font-semibold text-cyan-200">Pairing code: <span class="font-mono text-2xl">${escapeHtml(pair.pairing_code)}</span></p><p class="mt-2 text-xs text-slate-400">Expires ${new Date(pair.expires_at * 1000).toLocaleTimeString()}. Omi must provide the signed proof event before this identity is linked.</p><div class="mt-3 grid gap-2 sm:grid-cols-[1fr_1fr_1fr_auto]"><input id="omi-user-id" class="rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-xs" placeholder="Omi user ID"/><input id="omi-device-label" class="rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-xs" placeholder="Device label (optional)"/><input id="omi-proof" class="rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-xs" placeholder="Signed proof (production)"/><button id="omi-complete-pair" class="rounded-lg bg-emerald-500 px-3 py-2 text-xs font-bold text-slate-950">Complete</button></div><pre class="mt-3 overflow-auto rounded-lg bg-slate-950 p-3 text-[11px] text-slate-300">${escapeHtml(pair.webhook_paths.conversation)}</pre>`;
    document.getElementById('omi-complete-pair')?.addEventListener('click', async () => {
      const omiUserId = document.getElementById('omi-user-id')?.value?.trim();
      if (!omiUserId) return;
      const complete = await authorizedFetch('/api/omi/connections/pair/complete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ omi_user_id: omiUserId, pairing_code: pair.pairing_code, device_label: document.getElementById('omi-device-label')?.value?.trim(), proof_signature: document.getElementById('omi-proof')?.value?.trim() }) });
      if (!complete.ok) throw new Error('Pairing could not be completed.');
      output.classList.add('hidden');
      await load();
    });
    await load();
  });
  document.getElementById('omi-connections')?.addEventListener('click', async (event) => {
    const rotate = event.target.closest('[data-rotate]');
    const remove = event.target.closest('[data-delete]');
    if (rotate) { await authorizedFetch(`/api/omi/connections/${rotate.dataset.rotate}/rotate`, { method: 'POST' }); await load(); }
    if (remove) { await authorizedFetch(`/api/omi/connections/${remove.dataset.delete}`, { method: 'DELETE' }); await load(); }
  });
  await load();
}
