import { makeAuthCookie, passwordMatches } from '../../lib/dashboardAuth';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const password = req.body && typeof req.body.password === 'string' ? req.body.password : '';

  if (!passwordMatches(password)) {
    return res.redirect(303, '/login?error=1');
  }

  res.setHeader('Set-Cookie', makeAuthCookie());
  return res.redirect(303, '/');
}
