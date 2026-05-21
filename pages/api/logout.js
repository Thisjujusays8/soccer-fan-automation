export default function handler(req, res) {
  res.setHeader('Set-Cookie', 'dashboard_auth=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0');
  return res.redirect(303, '/login');
}
