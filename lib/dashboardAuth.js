import crypto from 'crypto';

const COOKIE_NAME = 'dashboard_auth';

function getPassword() {
  return process.env.DASHBOARD_PASSWORD || '';
}

function sign(value) {
  const password = getPassword();
  return crypto.createHmac('sha256', password).update(value).digest('hex');
}

export function dashboardAuthRequired() {
  return Boolean(getPassword());
}

export function makeAuthCookie() {
  const token = sign('approved');
  return `${COOKIE_NAME}=${token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800`;
}

export function requestIsAuthed(req) {
  const password = getPassword();
  if (!password) {
    return true;
  }

  const cookie = req.headers.cookie || '';
  const expected = sign('approved');
  return cookie.split(';').some(part => part.trim() === `${COOKIE_NAME}=${expected}`);
}

export function passwordMatches(value) {
  const password = getPassword();
  if (!password) {
    return true;
  }
  return value === password;
}
