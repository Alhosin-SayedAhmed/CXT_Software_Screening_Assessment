const path = require('path');
const crypto = require('crypto');
const express = require('express');
const { STAGES, isValidStage } = require('./stages');
const { createAuth } = require('./auth');

function normalizeOrderNumber(v) {
  if (v === undefined || v === null) return '';
  return String(v).trim().replace(/^#/, '').slice(0, 50);
}

function cleanText(v, max = 300) {
  if (v === undefined || v === null) return undefined;
  return String(v).trim().slice(0, max);
}

function createApp({ db, adminPassword, sessionSecret, webhookSecret = '', storeName = '', storeUrl = '', secureCookies = false }) {
  const app = express();
  const auth = createAuth({ password: adminPassword, secret: sessionSecret });

  app.disable('x-powered-by');
  app.set('trust proxy', 1);
  app.use(express.json({ limit: '200kb' }));

  app.use((req, res, next) => {
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('X-Frame-Options', 'DENY');
    res.setHeader('Referrer-Policy', 'same-origin');
    res.setHeader(
      'Content-Security-Policy',
      "default-src 'self'; img-src 'self' data:; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; script-src 'self'; connect-src 'self'; frame-ancestors 'none'"
    );
    next();
  });

  // ---------- عام: للعميل ----------
  app.get('/api/config', (req, res) => {
    res.json({ stages: STAGES, storeName, storeUrl });
  });

  // العميل بيشوف حالة الطلب بس — من غير اسم أو تليفون عشان الخصوصية
  app.get('/api/track/:number', (req, res) => {
    const order = db.getByNumber(normalizeOrderNumber(req.params.number));
    if (!order) return res.status(404).json({ error: 'رقم الطلب ده مش موجود. اتأكد من الرقم وجرب تاني.' });
    res.json({
      order_number: order.order_number,
      product: order.product,
      note: order.note,
      stage: order.stage,
      updated_at: order.updated_at,
      history: order.history,
    });
  });

  // ---------- الأدمن ----------
  app.post('/api/admin/login', (req, res) => {
    const ip = req.ip;
    if (auth.tooManyAttempts(ip)) {
      return res.status(429).json({ error: 'محاولات كتير غلط. جرب بعد ربع ساعة.' });
    }
    if (!auth.checkPassword(req.body && req.body.password)) {
      auth.recordFailure(ip);
      return res.status(401).json({ error: 'الباسورد غلط' });
    }
    auth.clearAttempts(ip);
    auth.login(res, secureCookies);
    res.json({ ok: true });
  });

  app.post('/api/admin/logout', (req, res) => {
    auth.logout(res, secureCookies);
    res.json({ ok: true });
  });

  app.get('/api/admin/me', (req, res) => res.json({ admin: auth.isAdmin(req) }));

  const admin = express.Router();
  admin.use(auth.requireAdmin);

  admin.get('/orders', (req, res) => {
    const search = cleanText(req.query.search, 100) || '';
    const stage = isValidStage(req.query.stage) ? req.query.stage : '';
    res.json({ orders: db.list({ search, stage }), counts: db.counts() });
  });

  admin.get('/orders/:id', (req, res) => {
    const order = db.getById(Number(req.params.id));
    if (!order) return res.status(404).json({ error: 'الطلب مش موجود' });
    res.json(order);
  });

  admin.post('/orders', (req, res) => {
    const b = req.body || {};
    const order_number = normalizeOrderNumber(b.order_number);
    if (!order_number) return res.status(400).json({ error: 'لازم تكتب رقم الطلب' });
    if (b.stage !== undefined && !isValidStage(b.stage)) return res.status(400).json({ error: 'مرحلة غير صحيحة' });
    if (db.getByNumber(order_number)) return res.status(409).json({ error: 'رقم الطلب ده متسجل قبل كده' });
    const order = db.createOrder({
      order_number,
      customer_name: cleanText(b.customer_name, 100),
      phone: cleanText(b.phone, 30),
      product: cleanText(b.product, 200),
      note: cleanText(b.note, 500),
      stage: b.stage,
    });
    res.status(201).json(order);
  });

  admin.patch('/orders/:id', (req, res) => {
    const b = req.body || {};
    if (b.stage !== undefined && !isValidStage(b.stage)) return res.status(400).json({ error: 'مرحلة غير صحيحة' });
    const order = db.updateOrder(Number(req.params.id), {
      customer_name: cleanText(b.customer_name, 100),
      phone: cleanText(b.phone, 30),
      product: cleanText(b.product, 200),
      note: cleanText(b.note, 500),
      stage: b.stage,
    });
    if (!order) return res.status(404).json({ error: 'الطلب مش موجود' });
    res.json(order);
  });

  admin.delete('/orders/:id', (req, res) => {
    if (!db.deleteOrder(Number(req.params.id))) return res.status(404).json({ error: 'الطلب مش موجود' });
    res.json({ ok: true });
  });

  app.use('/api/admin', admin);

  // ---------- (تجريبي) استقبال الطلبات أوتوماتيك من EasyOrders ----------
  // بيشتغل بس لو حطيت WEBHOOK_SECRET. الرابط اللي تحطه في EasyOrders:
  //   https://track.yourdomain.com/api/webhook/easyorders?key=WEBHOOK_SECRET
  // شكل البيانات اللي EasyOrders بتبعتها لازم يتجرب الأول (شوف README).
  app.post('/api/webhook/easyorders', (req, res) => {
    if (!webhookSecret) return res.status(404).json({ error: 'not enabled' });
    const key = String(req.query.key || req.get('x-webhook-key') || '');
    if (key.length === 0 || !timingEqual(key, webhookSecret)) {
      return res.status(401).json({ error: 'bad key' });
    }
    const body = req.body || {};
    const src = body.data && typeof body.data === 'object' ? { ...body, ...body.data } : body;
    const order_number = normalizeOrderNumber(
      src.short_id ?? src.order_number ?? src.order_id ?? src.number ?? src.id
    );
    console.log('[webhook] received keys:', Object.keys(src).join(', '), '→ order:', order_number || '(none)');
    if (!order_number) return res.status(400).json({ error: 'could not find order number in payload' });
    if (db.getByNumber(order_number)) return res.json({ ok: true, existed: true });

    const items = Array.isArray(src.cart_items) ? src.cart_items : Array.isArray(src.items) ? src.items : [];
    const product = items
      .map((it) => (it && (it.product?.name || it.name || it.title)) || '')
      .filter(Boolean)
      .join('، ');
    db.createOrder({
      order_number,
      customer_name: cleanText(src.full_name ?? src.customer_name ?? src.name, 100),
      phone: cleanText(src.phone ?? src.customer_phone, 30),
      product: cleanText(product, 200),
    });
    res.status(201).json({ ok: true, created: true });
  });

  // ---------- الصفحات ----------
  const pub = path.join(__dirname, '..', 'public');
  app.use(express.static(pub, { extensions: ['html'], maxAge: '1h' }));
  app.get('/track/:number', (req, res) => res.sendFile(path.join(pub, 'index.html')));
  app.use('/api', (req, res) => res.status(404).json({ error: 'not found' }));
  app.use((req, res) => res.status(404).sendFile(path.join(pub, 'index.html')));

  // eslint-disable-next-line no-unused-vars
  app.use((err, req, res, next) => {
    if (err.type === 'entity.parse.failed') return res.status(400).json({ error: 'invalid JSON' });
    console.error(err);
    res.status(500).json({ error: 'حصل خطأ في السيرفر' });
  });

  return app;
}

function timingEqual(a, b) {
  const ha = crypto.createHash('sha256').update(a).digest();
  const hb = crypto.createHash('sha256').update(b).digest();
  return crypto.timingSafeEqual(ha, hb);
}

module.exports = { createApp, normalizeOrderNumber };
