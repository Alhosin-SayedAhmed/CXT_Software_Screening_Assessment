const path = require('path');
const fs = require('fs');
const Database = require('better-sqlite3');
const { STAGE_KEYS, isValidStage } = require('./stages');

function openDb(file) {
  if (file !== ':memory:') fs.mkdirSync(path.dirname(file), { recursive: true });
  const db = new Database(file);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');

  db.exec(`
    CREATE TABLE IF NOT EXISTS orders (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      order_number  TEXT NOT NULL UNIQUE,
      customer_name TEXT NOT NULL DEFAULT '',
      phone         TEXT NOT NULL DEFAULT '',
      product       TEXT NOT NULL DEFAULT '',
      note          TEXT NOT NULL DEFAULT '',
      stage         TEXT NOT NULL,
      created_at    TEXT NOT NULL,
      updated_at    TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS stage_history (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id   INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
      stage      TEXT NOT NULL,
      changed_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_history_order ON stage_history(order_id);
  `);

  const q = {
    byNumber: db.prepare('SELECT * FROM orders WHERE order_number = ?'),
    byId: db.prepare('SELECT * FROM orders WHERE id = ?'),
    history: db.prepare('SELECT stage, changed_at FROM stage_history WHERE order_id = ? ORDER BY id'),
    list: db.prepare(`
      SELECT * FROM orders
      WHERE (@search = '' OR order_number LIKE @like OR customer_name LIKE @like OR phone LIKE @like)
        AND (@stage = '' OR stage = @stage)
      ORDER BY updated_at DESC, id DESC
      LIMIT 500`),
    insert: db.prepare(`
      INSERT INTO orders (order_number, customer_name, phone, product, note, stage, created_at, updated_at)
      VALUES (@order_number, @customer_name, @phone, @product, @note, @stage, @now, @now)`),
    insertHistory: db.prepare('INSERT INTO stage_history (order_id, stage, changed_at) VALUES (?, ?, ?)'),
    update: db.prepare(`
      UPDATE orders SET customer_name = @customer_name, phone = @phone, product = @product,
        note = @note, stage = @stage, updated_at = @now WHERE id = @id`),
    remove: db.prepare('DELETE FROM orders WHERE id = ?'),
    counts: db.prepare('SELECT stage, COUNT(*) AS n FROM orders GROUP BY stage'),
  };

  const now = () => new Date().toISOString();

  function withHistory(order) {
    if (!order) return null;
    return { ...order, history: q.history.all(order.id) };
  }

  const createOrder = db.transaction((data) => {
    const stage = data.stage || STAGE_KEYS[0];
    if (!isValidStage(stage)) throw new Error('INVALID_STAGE');
    const t = now();
    const info = q.insert.run({
      order_number: data.order_number,
      customer_name: data.customer_name || '',
      phone: data.phone || '',
      product: data.product || '',
      note: data.note || '',
      stage,
      now: t,
    });
    q.insertHistory.run(info.lastInsertRowid, stage, t);
    return withHistory(q.byId.get(info.lastInsertRowid));
  });

  const updateOrder = db.transaction((id, data) => {
    const current = q.byId.get(id);
    if (!current) return null;
    const merged = { ...current, ...pickDefined(data) };
    if (!isValidStage(merged.stage)) throw new Error('INVALID_STAGE');
    const t = now();
    q.update.run({ ...merged, id, now: t });
    if (merged.stage !== current.stage) q.insertHistory.run(id, merged.stage, t);
    return withHistory(q.byId.get(id));
  });

  return {
    raw: db,
    getByNumber: (n) => withHistory(q.byNumber.get(n)),
    getById: (id) => withHistory(q.byId.get(id)),
    list: ({ search = '', stage = '' } = {}) =>
      q.list.all({ search, like: `%${search}%`, stage }),
    counts: () => Object.fromEntries(q.counts.all().map((r) => [r.stage, r.n])),
    createOrder,
    updateOrder,
    deleteOrder: (id) => q.remove.run(id).changes > 0,
    close: () => db.close(),
  };
}

function pickDefined(obj) {
  const out = {};
  for (const k of ['customer_name', 'phone', 'product', 'note', 'stage']) {
    if (obj[k] !== undefined) out[k] = obj[k];
  }
  return out;
}

module.exports = { openDb };
