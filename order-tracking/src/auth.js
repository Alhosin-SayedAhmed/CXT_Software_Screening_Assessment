const crypto = require('crypto');

const COOKIE = 'admin_session';
const MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000; // أسبوع

function createAuth({ password, secret }) {
  const sign = (payload) =>
    crypto.createHmac('sha256', secret).update(payload).digest('base64url');

  function safeEqual(a, b) {
    const ha = crypto.createHash('sha256').update(String(a)).digest();
    const hb = crypto.createHash('sha256').update(String(b)).digest();
    return crypto.timingSafeEqual(ha, hb);
  }

  function issueToken() {
    const exp = Date.now() + MAX_AGE_MS;
    const payload = `admin.${exp}`;
    return `${payload}.${sign(payload)}`;
  }

  function verifyToken(token) {
    if (!token) return false;
    const i = token.lastIndexOf('.');
    if (i < 0) return false;
    const payload = token.slice(0, i);
    const sig = token.slice(i + 1);
    if (!safeEqual(sig, sign(payload))) return false;
    const exp = Number(payload.split('.')[1]);
    return Number.isFinite(exp) && exp > Date.now();
  }

  function readCookie(req) {
    const header = req.headers.cookie || '';
    for (const part of header.split(';')) {
      const [k, ...v] = part.trim().split('=');
      if (k === COOKIE) return decodeURIComponent(v.join('='));
    }
    return null;
  }

  function setCookie(res, value, maxAgeMs, secure) {
    const parts = [
      `${COOKIE}=${encodeURIComponent(value)}`,
      'Path=/',
      'HttpOnly',
      'SameSite=Strict',
      `Max-Age=${Math.floor(maxAgeMs / 1000)}`,
    ];
    if (secure) parts.push('Secure');
    res.setHeader('Set-Cookie', parts.join('; '));
  }

  // حماية بسيطة من تجربة باسوردات كتير: 10 محاولات غلط كل 15 دقيقة لكل IP
  const attempts = new Map();
  const WINDOW = 15 * 60 * 1000;
  function tooManyAttempts(ip) {
    const a = attempts.get(ip);
    if (!a || Date.now() - a.start > WINDOW) return false;
    return a.count >= 10;
  }
  function recordFailure(ip) {
    const a = attempts.get(ip);
    if (!a || Date.now() - a.start > WINDOW) attempts.set(ip, { start: Date.now(), count: 1 });
    else a.count++;
  }

  return {
    checkPassword: (p) => typeof p === 'string' && p.length > 0 && safeEqual(p, password),
    login(res, secure) {
      setCookie(res, issueToken(), MAX_AGE_MS, secure);
    },
    logout(res, secure) {
      setCookie(res, '', 0, secure);
    },
    isAdmin: (req) => verifyToken(readCookie(req)),
    requireAdmin(req, res, next) {
      if (verifyToken(readCookie(req))) return next();
      res.status(401).json({ error: 'غير مصرح. سجّل الدخول الأول.' });
    },
    tooManyAttempts,
    recordFailure,
    clearAttempts: (ip) => attempts.delete(ip),
  };
}

module.exports = { createAuth };
