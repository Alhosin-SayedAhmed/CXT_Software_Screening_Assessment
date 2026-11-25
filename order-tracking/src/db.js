const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');
const { STAGE_KEYS, isValidStage } = require('./stages');

const SCHEMA = fs.readFileSync(path.join(__dirname, '..', 'supabase', 'schema.sql'), 'utf8');

const ORDER_COLS = 'id, order_number, customer_name, phone, product, note, stage, created_at, updated_at';

function isLocalHost(connectionString) {
  try {
    const host = new URL(connectionString).hostname;
    return host === 'localhost' || host === '127.0.0.1' || host === '::1';
  } catch {
    return false;
  }
}

// connectionString: رابط الداتابيس من Supabase (Connect ← Connection string)
function openDb(connectionString, { ssl } = {}) {
  if (!connectionString) throw new Error('DATABASE_URL is required');
  const pool = new Pool({
    connectionString,
    // Supabase بيطلب اتصال مشفّر. الداتابيس اللي على جهازك مش محتاج.
    ssl: ssl ?? (isLocalHost(connectionString) ? false : { rejectUnauthorized: false }),
    max: 5,
    idleTimeoutMillis: 30000,
  });
  pool.on('error', (err) => console.error('[db] idle client error:', err.message));

  const one = async (sql, params) => (await pool.query(sql, params)).rows[0] || null;

  async function withHistory(order) {
    if (!order) return null;
    const { rows } = await pool.query(
      'SELECT stage, changed_at FROM public.stage_history WHERE order_id = $1 ORDER BY id',
      [order.id]
    );
    return { ...order, history: rows };
  }

  return {
    // بيعمل الجداول لو مش موجودة
    async init() {
      await pool.query(SCHEMA);
    },

    async getByNumber(n) {
      return withHistory(await one(`SELECT ${ORDER_COLS} FROM public.orders WHERE order_number = $1`, [n]));
    },

    async getById(id) {
      if (!Number.isInteger(id)) return null;
      return withHistory(await one(`SELECT ${ORDER_COLS} FROM public.orders WHERE id = $1`, [id]));
    },

    async list({ search = '', stage = '' } = {}) {
      const like = '%' + search.replace(/[\\%_]/g, (c) => '\\' + c) + '%';
      const { rows } = await pool.query(
        `SELECT ${ORDER_COLS} FROM public.orders
         WHERE ($1 = '' OR order_number ILIKE $2 OR customer_name ILIKE $2 OR phone ILIKE $2)
           AND ($3 = '' OR stage = $3)
         ORDER BY updated_at DESC, id DESC
         LIMIT 500`,
        [search, like, stage]
      );
      return rows;
    },

    async counts() {
      const { rows } = await pool.query('SELECT stage, COUNT(*)::int AS n FROM public.orders GROUP BY stage');
      return Object.fromEntries(rows.map((r) => [r.stage, r.n]));
    },

    // بيرجع null لو رقم الطلب متسجل قبل كده
    async createOrder(data) {
      const stage = data.stage || STAGE_KEYS[0];
      if (!isValidStage(stage)) throw new Error('INVALID_STAGE');
      const row = await one(
        `INSERT INTO public.orders (order_number, customer_name, phone, product, note, stage)
         VALUES ($1, $2, $3, $4, $5, $6)
         ON CONFLICT (order_number) DO NOTHING
         RETURNING ${ORDER_COLS}`,
        [data.order_number, data.customer_name || '', data.phone || '', data.product || '', data.note || '', stage]
      );
      return withHistory(row);
    },

    // الحقول اللي مش مبعوتة (undefined) بتفضل زي ما هي
    async updateOrder(id, data) {
      if (!Number.isInteger(id)) return null;
      if (data.stage !== undefined && !isValidStage(data.stage)) throw new Error('INVALID_STAGE');
      const row = await one(
        `UPDATE public.orders SET
           customer_name = COALESCE($2, customer_name),
           phone         = COALESCE($3, phone),
           product       = COALESCE($4, product),
           note          = COALESCE($5, note),
           stage         = COALESCE($6, stage)
         WHERE id = $1
         RETURNING ${ORDER_COLS}`,
        [id, data.customer_name ?? null, data.phone ?? null, data.product ?? null, data.note ?? null, data.stage ?? null]
      );
      return withHistory(row);
    },

    async deleteOrder(id) {
      if (!Number.isInteger(id)) return false;
      const res = await pool.query('DELETE FROM public.orders WHERE id = $1', [id]);
      return res.rowCount > 0;
    },

    close: () => pool.end(),
  };
}

module.exports = { openDb };
