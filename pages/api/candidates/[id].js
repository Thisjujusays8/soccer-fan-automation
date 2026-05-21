import { requestIsAuthed } from '../../../lib/dashboardAuth';
import { supabasePatch } from '../../../lib/supabaseRest';

const ALLOWED_STATUSES = new Set(['found', 'approved', 'rejected', 'processed', 'failed']);

function wantsHtml(req) {
  return String(req.headers.accept || '').includes('text/html');
}

function redirectBack(req, res) {
  const fallback = '/';
  const referer = req.headers.referer || fallback;
  return res.redirect(303, referer);
}

export default async function handler(req, res) {
  if (!requestIsAuthed(req)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { id } = req.query;
  const { status } = req.body || {};

  if (!id || typeof id !== 'string') {
    return res.status(400).json({ error: 'Missing candidate id' });
  }

  if (!ALLOWED_STATUSES.has(status)) {
    return res.status(400).json({ error: 'Invalid status' });
  }

  try {
    const rows = await supabasePatch(
      'clip_candidates',
      `id=eq.${encodeURIComponent(id)}`,
      { status, error_message: null }
    );

    if (!rows || rows.length === 0) {
      return res.status(404).json({ error: 'Candidate not found' });
    }

    if (wantsHtml(req)) {
      return redirectBack(req, res);
    }

    return res.status(200).json({ candidate: rows[0] });
  } catch (error) {
    return res.status(500).json({ error: error.message });
  }
}
