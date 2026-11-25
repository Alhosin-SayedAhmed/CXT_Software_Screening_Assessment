const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { Client } = require('pg');
const { openDb } = require('../src/db');
const { createApp } = require('../src/app');

// الاختبارات بتشتغل على داتابيس Postgres حقيقية (نفس اللي جوه Supabase).
// ماتشغّلهاش على داتابيس الإنتاج: الاختبار بيمسح الجداول.
const TEST_DB = process.env.TEST_DATABASE_URL || 'postgresql://tracker:tracker@localhost:5432/tracker_test';

let server, base, db, sql;

before(async () => {
  sql = new Client({ connectionString: TEST_DB });
  await sql.connect();
  await sql.query('DROP TABLE IF EXISTS public.stage_history, public.orders CASCADE');
  db = openDb(TEST_DB);
  await db.init();
  await db.init(); // التأكد إن تشغيل الـ schema مرتين مفيهوش مشكلة
  const app = createApp({ db, adminPassword: 'secret-pass-123', sessionSecret: 'x'.repeat(32), webhookSecret: 'hook-key' });
  await new Promise((r) => { server = app.listen(0, r); });
  base = `http://127.0.0.1:${server.address().port}`;
});

after(async () => { server.close(); await db.close(); await sql.end(); });

const json = (method, body, cookie) => ({
  method,
  headers: { 'Content-Type': 'application/json', ...(cookie ? { Cookie: cookie } : {}) },
  body: body ? JSON.stringify(body) : undefined,
});

async function login() {
  const res = await fetch(base + '/api/admin/login', json('POST', { password: 'secret-pass-123' }));
  assert.equal(res.status, 200);
  return res.headers.get('set-cookie').split(';')[0];
}

test('admin routes require login', async () => {
  const res = await fetch(base + '/api/admin/orders');
  assert.equal(res.status, 401);
});

test('wrong password rejected', async () => {
  const res = await fetch(base + '/api/admin/login', json('POST', { password: 'nope' }));
  assert.equal(res.status, 401);
});

test('forged cookie rejected', async () => {
  const res = await fetch(base + '/api/admin/orders', { headers: { Cookie: 'admin_session=admin.9999999999999.fake' } });
  assert.equal(res.status, 401);
});

test('full flow: create, track, change stage, history', async () => {
  const cookie = await login();

  let res = await fetch(base + '/api/admin/orders', json('POST', {
    order_number: '#10234', customer_name: 'أحمد', phone: '01000000000', product: 'باور بانك 20000',
  }, cookie));
  assert.equal(res.status, 201);
  const created = await res.json();
  assert.equal(created.order_number, '10234');
  assert.equal(created.stage, 'received');

  res = await fetch(base + '/api/admin/orders', json('POST', { order_number: '10234' }, cookie));
  assert.equal(res.status, 409);

  res = await fetch(base + '/api/track/10234');
  assert.equal(res.status, 200);
  let pub = await res.json();
  assert.equal(pub.stage, 'received');
  assert.equal(pub.product, 'باور بانك 20000');
  assert.equal(pub.customer_name, undefined, 'customer name must not be public');
  assert.equal(pub.phone, undefined, 'phone must not be public');

  res = await fetch(base + `/api/admin/orders/${created.id}`, json('PATCH', { stage: 'manufacturing', note: 'هيخلص الخميس' }, cookie));
  assert.equal(res.status, 200);

  res = await fetch(base + `/api/admin/orders/${created.id}`, json('PATCH', { stage: 'flying' }, cookie));
  assert.equal(res.status, 400);

  pub = await (await fetch(base + '/api/track/%2310234')).json();
  assert.equal(pub.stage, 'manufacturing');
  assert.equal(pub.note, 'هيخلص الخميس');
  assert.deepEqual(pub.history.map((h) => h.stage), ['received', 'manufacturing']);

  const list = await (await fetch(base + '/api/admin/orders?search=أحمد', { headers: { Cookie: cookie } })).json();
  assert.equal(list.orders.length, 1);
  assert.equal(list.counts.manufacturing, 1);

  res = await fetch(base + `/api/admin/orders/${created.id}`, json('DELETE', null, cookie));
  assert.equal(res.status, 200);
  res = await fetch(base + '/api/track/10234');
  assert.equal(res.status, 404);
});

test('unknown order returns 404 with Arabic message', async () => {
  const res = await fetch(base + '/api/track/999999');
  assert.equal(res.status, 404);
  assert.match((await res.json()).error, /مش موجود/);
});

test('pages are served', async () => {
  for (const p of ['/', '/admin', '/track/123']) {
    const res = await fetch(base + p);
    assert.equal(res.status, 200, p);
    assert.match(res.headers.get('content-type'), /text\/html/);
  }
});

test('webhook needs key and creates order', async () => {
  let res = await fetch(base + '/api/webhook/easyorders', json('POST', { id: '555' }));
  assert.equal(res.status, 401);
  res = await fetch(base + '/api/webhook/easyorders?key=hook-key', json('POST', {
    short_id: 777, full_name: 'منى', phone: '01111111111', cart_items: [{ product: { name: 'باور بانك' } }],
  }));
  assert.equal(res.status, 201);
  const pub = await (await fetch(base + '/api/track/777')).json();
  assert.equal(pub.stage, 'received');
  assert.equal(pub.product, 'باور بانك');
});

test('edits made directly in Supabase show up on the site', async () => {
  const cookie = await login();
  const res = await fetch(base + '/api/admin/orders', json('POST', { order_number: '3001', product: 'باور بانك' }, cookie));
  assert.equal(res.status, 201);

  // كأنك غيّرت المرحلة بإيدك من Table Editor في Supabase
  await sql.query("UPDATE public.orders SET stage = 'quality', note = 'اتعدلت من Supabase' WHERE order_number = '3001'");

  const pub = await (await fetch(base + '/api/track/3001')).json();
  assert.equal(pub.stage, 'quality');
  assert.equal(pub.note, 'اتعدلت من Supabase');
  assert.deepEqual(pub.history.map((h) => h.stage), ['received', 'quality'], 'trigger logs stage changes');

  // تعديل حاجة غير المرحلة مايزوّدش سجل جديد
  await sql.query("UPDATE public.orders SET product = 'باور بانك 2' WHERE order_number = '3001'");
  const again = await (await fetch(base + '/api/track/3001')).json();
  assert.equal(again.history.length, 2);
  assert.ok(new Date(again.updated_at) >= new Date(pub.updated_at));
});

test('row level security is on (public Supabase keys cannot read orders)', async () => {
  const { rows } = await sql.query(
    "SELECT relname, relrowsecurity FROM pg_class WHERE relname IN ('orders', 'stage_history') ORDER BY relname"
  );
  assert.deepEqual(rows, [
    { relname: 'orders', relrowsecurity: true },
    { relname: 'stage_history', relrowsecurity: true },
  ]);
});

test('search treats % and _ literally', async () => {
  const cookie = await login();
  const list = await (await fetch(base + '/api/admin/orders?search=%25', { headers: { Cookie: cookie } })).json();
  assert.equal(list.orders.length, 0);
});

test('API responses are not cached', async () => {
  const res = await fetch(base + '/api/track/3001');
  assert.equal(res.headers.get('cache-control'), 'no-store');
});
