import { authorizedFetch } from '../api.js';
import { getSession, signOut } from '../supabase.js';

export async function renderAccount(container) {
  let userEmail = 'masoodmashu823@gmail.com';
  let userId = 'f7550f35-5d54-442e-b1ec-b3806b1a7c81';

  try {
    const { session } = await getSession();
    if (session?.user) {
      userEmail = session.user.email || userEmail;
      userId = session.user.id || userId;
    }
  } catch (_) {}

  container.innerHTML = `
    <div class="mx-auto max-w-3xl space-y-6 animate-fade-in">
      <div>
        <p class="text-xs font-mono-tech uppercase tracking-widest text-cyan-300">Workspace settings</p>
        <h1 class="mt-2 text-3xl font-bold text-white">Account & Authentication</h1>
        <p class="mt-2 text-sm text-slate-400">
          Your Omi meetings, ambient memories, Lyzr agent traces, action items, and wearable connections belong to this secure workspace.
        </p>
      </div>

      <!-- Account Profile Overview -->
      <section class="rounded-2xl border border-white/10 bg-white/[.03] p-6 space-y-4">
        <h2 class="font-semibold text-lg text-white flex items-center gap-2">
          <svg class="w-5 h-5 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          Account Profile
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="p-3.5 rounded-xl bg-slate-900/60 border border-white/5">
            <div class="text-[11px] font-mono-tech text-slate-500 uppercase">Authenticated Email</div>
            <div class="mt-1 text-sm font-semibold text-slate-200 break-all">${userEmail}</div>
          </div>
          <div class="p-3.5 rounded-xl bg-slate-900/60 border border-white/5">
            <div class="text-[11px] font-mono-tech text-slate-500 uppercase">Account UUID</div>
            <div class="mt-1 text-xs font-mono-tech text-cyan-300 break-all">${userId}</div>
          </div>
        </div>
      </section>

      <!-- Active Session & Logout -->
      <section class="rounded-2xl border border-teal-500/20 bg-teal-950/10 p-6 space-y-4">
        <div class="flex items-start justify-between">
          <div>
            <h2 class="font-semibold text-lg text-white flex items-center gap-2">
              <svg class="w-5 h-5 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              Session Management
            </h2>
            <p class="mt-1 text-sm text-slate-400">
              Sign out to end your current authenticated session on this browser device.
            </p>
          </div>
        </div>

        <div>
          <button id="btn-account-signout" class="px-5 py-2.5 rounded-xl bg-gradient-to-r from-rose-500 to-rose-600 hover:from-rose-600 hover:to-rose-700 text-white font-medium text-xs shadow-lg shadow-rose-900/30 transition flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            <span>Sign Out of OMIMIND</span>
          </button>
        </div>
      </section>

      <!-- Danger Zone -->
      <section class="rounded-2xl border border-rose-500/20 bg-rose-950/10 p-6 space-y-4">
        <div>
          <h2 class="font-semibold text-lg text-rose-300">Danger Zone</h2>
          <p class="mt-1 text-sm leading-6 text-slate-400">
            Permanently delete your account. This removes all Qdrant vector memories, Postgres workspace rows, Omi device pairings, and Lyzr swarm run history. This action cannot be undone.
          </p>
        </div>
        <button id="delete-account" class="rounded-xl border border-rose-400/40 bg-rose-950/30 px-4 py-2 text-xs font-bold text-rose-200 hover:bg-rose-900/40 transition">
          Delete my account
        </button>
      </section>
    </div>
  `;

  document.getElementById('btn-account-signout')?.addEventListener('click', async () => {
    await signOut();
    window.location.hash = '';
    window.location.reload();
  });

  document.getElementById('delete-account')?.addEventListener('click', async () => {
    if (!window.confirm('Delete your OMIMIND account and all workspace data?')) return;
    const response = await authorizedFetch('/api/account', { method: 'DELETE' });
    if (!response.ok) throw new Error('Account deletion failed.');
    await signOut();
    window.location.hash = '';
    window.location.reload();
  });
}
