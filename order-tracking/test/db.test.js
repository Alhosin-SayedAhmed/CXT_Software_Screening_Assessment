// اختبارات قواعد الحماية في supabase/schema.sql على Postgres حقيقية.
// محتاجة داتابيس للتجربة بس (الاختبار بيمسح الجداول) — أوعى تحط رابط Supabase بتاعك.
//   TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/tracker_test npm test
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { Client } = require('pg');

const TEST_DB = process.env.TEST_DATABASE_URL || 'postgresql://tracker:tracker@localhost:5432/tracker_test';
const read = (f) => fs.readFileSync(path.join(__dirname, '..', f), 'utf8');

let pg;
let adminId;
let strangerId;

// بيشغّل SQL كأنه جاي من الموقع: زائر (anon) أو مستخدم مسجّل دخول
async function as(who, sql, params = []) {
  await pg.query('BEGIN');
  try {
    if (who === 'anon') {
      await pg.query("SET LOCAL ROLE anon");
    } else {
      await pg.query('SET LOCAL ROLE authenticated');
      await pg.query("SELECT set_config('request.jwt.claims', $1, true)", [JSON.stringify({ sub: who, role: 'authenticated' })]);
    }
    const res = await pg.query(sql, params);
    await pg.query('COMMIT');
    return res;
  } catch (err) {
    await pg.query('ROLLBACK');
    throw err;
  }
}

before(async () => {
  pg = new Client({ connectionString: TEST_DB });
  await pg.connect();
  await pg.query('DROP TABLE IF EXISTS public.stage_history, public.orders, public.admins, public.stages CASCADE');
  await pg.query('DROP SCHEMA IF EXISTS auth CASCADE');
  await pg.query(read('test/supabase-stub.sql'));
  await pg.query(read('supabase/schema.sql'));
  await pg.query(read('supabase/schema.sql')); // تشغيله مرتين لازم يبقى آمن

  adminId = (await pg.query("INSERT INTO auth.users (email) VALUES ('owner@test.local') RETURNING id")).rows[0].id;
  strangerId = (await pg.query("INSERT INTO auth.users (email) VALUES ('stranger@test.local') RETURNING id")).rows[0].id;
  // نفس السطر اللي في آخر schema.sql
  await pg.query("insert into public.admins (user_id) select id from auth.users where email = 'owner@test.local'");
});

after(async () => { await pg.end(); });

test('stages are seeded once and readable by visitors', async () => {
  const { rows } = await as('anon', 'SELECT key FROM public.stages ORDER BY position');
  assert.deepEqual(rows.map((r) => r.key), ['received', 'preparing', 'manufacturing', 'quality', 'completed', 'shipping', 'delivered']);
});

test('admin can add, update, list and delete orders', async () => {
  const ins = await as(adminId, "INSERT INTO public.orders (order_number, customer_name, phone, product) VALUES ('10234', 'أحمد', '01000000000', 'باور بانك') RETURNING id, stage");
  assert.equal(ins.rows[0].stage, 'received');
  const id = ins.rows[0].id;

  await as(adminId, "UPDATE public.orders SET stage = 'manufacturing', note = 'الخميس' WHERE id = $1", [id]);
  const list = await as(adminId, "SELECT * FROM public.admin_list_orders('أحمد', '')");
  assert.equal(list.rows.length, 1);
  assert.equal(list.rows[0].stage, 'manufacturing');

  const counts = await as(adminId, 'SELECT * FROM public.admin_order_counts()');
  assert.deepEqual(counts.rows, [{ stage: 'manufacturing', n: 1 }]);

  const hist = await as(adminId, 'SELECT stage FROM public.stage_history WHERE order_id = $1 ORDER BY id', [id]);
  assert.deepEqual(hist.rows.map((r) => r.stage), ['received', 'manufacturing']);

  const del = await as(adminId, 'DELETE FROM public.orders WHERE id = $1 RETURNING id', [id]);
  assert.equal(del.rowCount, 1);
});

test('customer can track one order — without name or phone', async () => {
  await as(adminId, "INSERT INTO public.orders (order_number, customer_name, phone, product, stage) VALUES ('555', 'منى', '01111111111', 'باور بانك', 'quality')");
  const { rows } = await as('anon', 'SELECT public.track_order($1) AS o', ['#555 ']);
  const o = rows[0].o;
  assert.equal(o.order_number, '555');
  assert.equal(o.stage, 'quality');
  assert.equal(o.product, 'باور بانك');
  assert.equal(o.customer_name, undefined);
  assert.equal(o.phone, undefined);
  assert.deepEqual(o.history.map((h) => h.stage), ['quality']);

  const missing = await as('anon', 'SELECT public.track_order($1) AS o', ['999999']);
  assert.equal(missing.rows[0].o, null);
});

test('visitors cannot read or change orders directly', async () => {
  await assert.rejects(as('anon', 'SELECT * FROM public.orders'), /permission denied/);
  await assert.rejects(as('anon', 'SELECT * FROM public.stage_history'), /permission denied/);
  await assert.rejects(as('anon', "INSERT INTO public.orders (order_number) VALUES ('hack')"), /permission denied/);
  await assert.rejects(as('anon', "SELECT * FROM public.admin_list_orders('', '')"), /permission denied/);
  const upd = await as('anon', "UPDATE public.stages SET label = 'x'");
  assert.equal(upd.rowCount, 0, 'RLS: visitors can read stages but change nothing');
  const { rows } = await as('anon', "SELECT label FROM public.stages WHERE key = 'received'");
  assert.equal(rows[0].label, 'تم استلام الطلب');
});

test('logged-in users who are not admins see nothing and cannot write', async () => {
  const sel = await as(strangerId, 'SELECT * FROM public.orders');
  assert.equal(sel.rowCount, 0);
  const list = await as(strangerId, "SELECT * FROM public.admin_list_orders('', '')");
  assert.equal(list.rowCount, 0);
  const upd = await as(strangerId, "UPDATE public.orders SET stage = 'delivered'");
  assert.equal(upd.rowCount, 0);
  await assert.rejects(as(strangerId, "INSERT INTO public.orders (order_number) VALUES ('x1')"), /row-level security/);
  await assert.rejects(as(strangerId, 'INSERT INTO public.admins (user_id) VALUES ($1)', [strangerId]), /row-level security/);
  const isAdmin = await as(strangerId, 'SELECT public.is_admin() AS a');
  assert.equal(isAdmin.rows[0].a, false);
  const ownerIsAdmin = await as(adminId, 'SELECT public.is_admin() AS a');
  assert.equal(ownerIsAdmin.rows[0].a, true);
});

test('edits made in the Supabase dashboard are logged too', async () => {
  // الـ Table Editor بيعدّل بصلاحيات صاحب الداتابيس
  await pg.query("UPDATE public.orders SET stage = 'shipping' WHERE order_number = '555'");
  await pg.query("UPDATE public.orders SET product = 'باور بانك 2' WHERE order_number = '555'");
  const { rows } = await as('anon', "SELECT public.track_order('555') AS o");
  assert.deepEqual(rows[0].o.history.map((h) => h.stage), ['quality', 'shipping']);
  assert.equal(rows[0].o.product, 'باور بانك 2');
});

test('invalid stage and duplicate order number are rejected', async () => {
  await assert.rejects(as(adminId, "INSERT INTO public.orders (order_number, stage) VALUES ('777', 'flying')"), (e) => e.code === '23503');
  await assert.rejects(as(adminId, "INSERT INTO public.orders (order_number) VALUES ('555')"), (e) => e.code === '23505');
});

test('search treats % and _ literally', async () => {
  const { rowCount } = await as(adminId, "SELECT * FROM public.admin_list_orders('%', '')");
  assert.equal(rowCount, 0);
});
