let clientPromise;

async function getClient() {
  if (!clientPromise) {
    clientPromise = fetch('/api/auth/config')
      .then((response) => response.json())
      .then(async (config) => {
        if (!config.supabase_url || !config.publishable_key) return null;
        const { createClient } = await import('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.49.1/+esm');
        return createClient(config.supabase_url, config.publishable_key, {
          auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
        });
      });
  }
  return clientPromise;
}

export async function getSession() {
  const client = await getClient();
  if (!client) return { session: null, configured: false };
  const { data, error } = await client.auth.getSession();
  if (error) throw error;
  return { session: data.session, configured: true };
}

export async function signIn(email, password) {
  const client = await getClient();
  if (!client) throw new Error('Supabase Auth is not configured on this deployment.');
  const { data, error } = await client.auth.signInWithPassword({ email, password });
  if (error) throw error;
  return data;
}

export async function signUp(email, password, displayName = '') {
  const client = await getClient();
  if (!client) throw new Error('Supabase Auth is not configured on this deployment.');
  const { data, error } = await client.auth.signUp({ email, password, options: { data: { display_name: displayName } } });
  if (error) throw error;
  return data;
}

export async function resetPassword(email) {
  const client = await getClient();
  if (!client) throw new Error('Supabase Auth is not configured on this deployment.');
  const { error } = await client.auth.resetPasswordForEmail(email, { redirectTo: `${window.location.origin}/#account` });
  if (error) throw error;
}

export async function updatePassword(password) {
  const client = await getClient();
  if (!client) throw new Error('Supabase Auth is not configured on this deployment.');
  const { data, error } = await client.auth.updateUser({ password });
  if (error) throw error;
  return data;
}

export async function signOut() {
  const client = await getClient();
  if (client) {
    const { error } = await client.auth.signOut();
    if (error) throw error;
  }
}

export async function onAuthStateChange(callback) {
  const client = await getClient();
  if (!client) return () => {};
  const { data } = client.auth.onAuthStateChange(callback);
  return () => data.subscription.unsubscribe();
}

export async function getAccessToken() {
  const { session } = await getSession();
  return session?.access_token || null;
}
