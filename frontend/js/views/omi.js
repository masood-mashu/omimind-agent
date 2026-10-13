import { authorizedFetch } from '../api.js';
import { showToast } from '../components/toast.js';

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
}

export async function renderOmi(container) {
  const host = window.location.hostname;
  const port = window.location.port ? `:${window.location.port}` : '';
  const currentOrigin = `${window.location.protocol}//${host}${port}`;

  container.innerHTML = `
    <div class="mx-auto max-w-4xl space-y-6">
      <div>
        <p class="text-xs font-mono-tech uppercase tracking-widest text-teal-400">Workspace connection</p>
        <h1 class="mt-2 text-2xl sm:text-3xl font-bold text-white">Connect Omi Wearable</h1>
        <p class="mt-1 text-sm text-slate-400">
          Pair your Omi device with your OMIMIND workspace so ambient conversations flow automatically into Qdrant vector memory.
        </p>
      </div>

      <!-- Hotspot / Network Notice -->
      <div class="rounded-2xl border border-teal-500/20 bg-teal-500/5 p-4 flex items-start gap-3 text-xs text-slate-300">
        <span class="text-teal-400 text-base">📶</span>
        <div class="space-y-1">
          <p class="font-semibold text-teal-200">Mobile Hotspot Direct Connection</p>
          <p class="text-slate-400 leading-relaxed">
            Since your phone is acting as a hotspot for this laptop, your laptop is directly reachable by your phone at:
            <code class="px-1.5 py-0.5 rounded bg-slate-900 border border-white/10 text-teal-300 font-mono-tech">http://10.156.188.136:8000</code>
          </p>
        </div>
      </div>

      <!-- One-time pairing section -->
      <section class="rounded-2xl border border-white/10 bg-slate-900/60 p-5 space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="font-semibold text-white">Pair New Omi Device</h2>
            <p class="mt-1 text-xs text-slate-400">Generate a 6-digit code to pair with your Omi user ID.</p>
          </div>
          <button id="omi-start-pair" class="rounded-xl btn-mint-cta px-4 py-2 text-xs">
            Start pairing
          </button>
        </div>
        <div id="omi-pair-output" class="hidden rounded-xl border border-teal-400/20 bg-teal-400/5 p-4 text-sm space-y-3"></div>
      </section>

      <!-- Active Webhook Token Display (Shows when rotated) -->
      <div id="omi-webhook-url-box" class="hidden rounded-2xl border border-teal-500/30 bg-[#0e131f] p-5 space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="text-xs font-bold text-teal-300 uppercase tracking-wider font-mono-tech">Your Omi Webhook URL</h3>
          <span class="text-[10px] text-slate-400 font-mono-tech">Paste into Omi App</span>
        </div>
        <div class="flex items-center gap-2 bg-slate-950 p-2.5 rounded-xl border border-white/10">
          <code id="omi-webhook-full-url" class="text-xs text-teal-300 font-mono-tech break-all flex-1 select-all"></code>
          <button id="btn-copy-webhook-url" class="px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold flex-shrink-0 transition">
            Copy URL
          </button>
        </div>
      </div>

      <!-- Paired Devices -->
      <section class="rounded-2xl border border-white/10 bg-slate-900/60 p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="font-semibold text-white">Paired Devices</h2>
          <span class="text-xs text-slate-400 font-mono-tech">Multi-tenant verified</span>
        </div>
        <div id="omi-connections" class="space-y-3">
          <p class="text-sm text-slate-500">Loading connections…</p>
        </div>
      </section>
    </div>
  `;

  const output = document.getElementById('omi-pair-output');
  const urlBox = document.getElementById('omi-webhook-url-box');
  const fullUrlEl = document.getElementById('omi-webhook-full-url');
  const copyBtn = document.getElementById('btn-copy-webhook-url');

  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      const urlText = fullUrlEl?.innerText || '';
      if (urlText) {
        navigator.clipboard.writeText(urlText).then(() => {
          showToast('Webhook URL copied to clipboard!', 'success');
        });
      }
    });
  }

  const load = async () => {
    try {
      const response = await authorizedFetch('/api/omi/connections');
      const data = await response.json();
      const target = document.getElementById('omi-connections');
      if (!data.connections?.length) {
        target.innerHTML = '<p class="text-sm text-slate-500">No Omi connection paired yet.</p>';
        return;
      }
      target.innerHTML = data.connections.map((item) => `
        <div class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-slate-950/70 p-4">
          <div>
            <p class="text-sm font-semibold text-white flex items-center gap-2">
              <span>${escapeHtml(item.device_label || 'Omi Device')}</span>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-mono-tech bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                ${escapeHtml(item.status)}
              </span>
            </p>
            <p class="text-xs text-slate-400 font-mono-tech mt-1">
              Omi ID: <span class="text-slate-200">${escapeHtml(item.omi_user_id || 'Pending')}</span>
            </p>
          </div>
          <div class="flex gap-2">
            <button data-rotate="${escapeHtml(item.id)}" class="rounded-lg border border-teal-500/30 bg-teal-500/10 hover:bg-teal-500/20 px-3 py-1.5 text-xs text-teal-300 transition">
              Get Webhook URL
            </button>
            <button data-delete="${escapeHtml(item.id)}" class="rounded-lg border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 px-3 py-1.5 text-xs text-rose-300 transition">
              Revoke
            </button>
          </div>
        </div>
      `).join('');
    } catch (err) {
      const target = document.getElementById('omi-connections');
      if (target) target.innerHTML = `<p class="text-xs text-rose-400">Error loading devices: ${escapeHtml(err.message)}</p>`;
    }
  };

  document.getElementById('omi-start-pair')?.addEventListener('click', async () => {
    try {
      const response = await authorizedFetch('/api/omi/connections/pair/start', { method: 'POST' });
      const pair = await response.json();
      output.classList.remove('hidden');
      output.innerHTML = `
        <p class="font-semibold text-teal-300">Pairing code: <span class="font-mono text-2xl text-white ml-2">${escapeHtml(pair.pairing_code)}</span></p>
        <p class="mt-1 text-xs text-slate-400">Expires ${new Date(pair.expires_at * 1000).toLocaleTimeString()}. Enter your Omi User ID below:</p>
        <div class="mt-3 grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
          <input id="omi-user-id" class="rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-xs text-white" placeholder="Omi User ID" value="uoCU1OLVdUaEU9lxVSICTbakkiD3"/>
          <input id="omi-device-label" class="rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-xs text-white" placeholder="Device label (optional)" value="My Omi Device"/>
          <button id="omi-complete-pair" class="rounded-lg bg-teal-500 hover:bg-teal-400 px-4 py-2 text-xs font-bold text-slate-950 transition">Complete</button>
        </div>
      `;

      document.getElementById('omi-complete-pair')?.addEventListener('click', async () => {
        const omiUserId = document.getElementById('omi-user-id')?.value?.trim();
        if (!omiUserId) {
          showToast('Enter your Omi User ID', 'warning');
          return;
        }
        const complete = await authorizedFetch('/api/omi/connections/pair/complete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            omi_user_id: omiUserId,
            pairing_code: pair.pairing_code,
            device_label: document.getElementById('omi-device-label')?.value?.trim(),
          })
        });
        if (!complete.ok) throw new Error('Pairing could not be completed.');
        showToast('Omi device successfully paired!', 'success');
        output.classList.add('hidden');
        await load();
      });
    } catch (err) {
      showToast('Pairing error: ' + err.message, 'warning');
    }
  });

  document.getElementById('omi-connections')?.addEventListener('click', async (event) => {
    const rotate = event.target.closest('[data-rotate]');
    const remove = event.target.closest('[data-delete]');
    if (rotate) {
      try {
        const res = await authorizedFetch(`/api/omi/connections/${rotate.dataset.rotate}/rotate`, { method: 'POST' });
        const rotatedData = await res.json();
        if (urlBox && fullUrlEl) {
          const webhookUrl = `http://10.156.188.136:8000${rotatedData.webhook_paths.conversation}`;
          fullUrlEl.innerText = webhookUrl;
          urlBox.classList.remove('hidden');
          urlBox.scrollIntoView({ behavior: 'smooth' });
          showToast('Webhook URL generated! Copy and paste into your Omi mobile app.', 'success');
        }
        await load();
      } catch (err) {
        showToast('Failed to generate webhook URL: ' + err.message, 'warning');
      }
    }
    if (remove) {
      try {
        await authorizedFetch(`/api/omi/connections/${remove.dataset.delete}`, { method: 'DELETE' });
        showToast('Device connection revoked.');
        await load();
      } catch (err) {
        showToast('Failed to revoke: ' + err.message, 'warning');
      }
    }
  });

  await load();
}
