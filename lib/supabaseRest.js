const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY;

function requireSupabaseEnv() {
  if (!SUPABASE_URL || !SUPABASE_SERVICE_KEY) {
    throw new Error('Missing SUPABASE_URL and SUPABASE_SERVICE_KEY');
  }
}

function headers(extra = {}) {
  requireSupabaseEnv();
  return {
    apikey: SUPABASE_SERVICE_KEY,
    Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
    'Content-Type': 'application/json',
    ...extra
  };
}

export async function supabaseGet(path, params = '') {
  requireSupabaseEnv();
  const url = `${SUPABASE_URL.replace(/\/$/, '')}/rest/v1/${path}${params ? `?${params}` : ''}`;
  const response = await fetch(url, { headers: headers() });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Supabase GET failed ${response.status}: ${body}`);
  }
  return response.json();
}

export async function supabasePatch(path, params, payload) {
  requireSupabaseEnv();
  const url = `${SUPABASE_URL.replace(/\/$/, '')}/rest/v1/${path}?${params}`;
  const response = await fetch(url, {
    method: 'PATCH',
    headers: headers({ Prefer: 'return=representation' }),
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Supabase PATCH failed ${response.status}: ${body}`);
  }
  return response.json();
}
