import { requestIsAuthed } from '../../lib/dashboardAuth';
import { supabaseGet } from '../../lib/supabaseRest';

function envStatus() {
  return {
    supabaseUrl: Boolean(process.env.SUPABASE_URL),
    supabaseKey: Boolean(process.env.SUPABASE_KEY),
    supabaseServiceKey: Boolean(process.env.SUPABASE_SERVICE_KEY),
    dashboardPassword: Boolean(process.env.DASHBOARD_PASSWORD),
    videoBucket: process.env.VIDEO_BUCKET || 'videos'
  };
}

export default async function handler(req, res) {
  if (!requestIsAuthed(req)) {
    return res.status(401).json({ ok: false, error: 'Unauthorized' });
  }

  const env = envStatus();
  const checks = {
    env,
    players: false,
    candidates: false,
    posts: false
  };

  try {
    await supabaseGet('players', 'select=slug&limit=1');
    checks.players = true;
  } catch (error) {
    checks.playersError = error.message;
  }

  try {
    await supabaseGet('clip_candidates', 'select=id&limit=1');
    checks.candidates = true;
  } catch (error) {
    checks.candidatesError = error.message;
  }

  try {
    await supabaseGet('posts', 'select=id&limit=1');
    checks.posts = true;
  } catch (error) {
    checks.postsError = error.message;
  }

  const ok = env.supabaseUrl && (env.supabaseServiceKey || env.supabaseKey) && checks.players && checks.candidates && checks.posts;

  return res.status(ok ? 200 : 500).json({ ok, checks });
}
