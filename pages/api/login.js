import { makeAuthCookie, passwordMatches } from '../../lib/dashboardAuth';

function parseForm(body) {
  return new URLSearchParams(body || '');
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
  }

  const body = Buffer.concat(chunks).toString('utf-8');
  const form = parseForm(body);
  const password = form.get('password') || '';

  if (!passwordMatches(password)) {
    return res.redirect(303, '/login?error=1');
  }

  res.setHeader('Set-Cookie', makeAuthCookie());
  return res.redirect(303, '/');
}
