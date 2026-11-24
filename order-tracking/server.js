const path = require('path');
const crypto = require('crypto');
const { openDb } = require('./src/db');
const { createApp } = require('./src/app');

// تحميل ملف .env لو موجود (من غير مكتبات إضافية)
try { process.loadEnvFile(path.join(__dirname, '.env')); } catch { /* مفيش .env — عادي */ }

const PORT = Number(process.env.PORT) || 3000;
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD;
const IS_PROD = process.env.NODE_ENV === 'production';

if (!ADMIN_PASSWORD || ADMIN_PASSWORD.length < 8) {
  console.error('❌ لازم تحط ADMIN_PASSWORD (8 حروف على الأقل) في ملف .env أو في إعدادات الاستضافة.');
  process.exit(1);
}

let SESSION_SECRET = process.env.SESSION_SECRET;
if (!SESSION_SECRET) {
  if (IS_PROD) {
    console.error('❌ لازم تحط SESSION_SECRET (كلام عشوائي طويل) في إعدادات الاستضافة.');
    process.exit(1);
  }
  SESSION_SECRET = crypto.randomBytes(32).toString('hex');
}

const DB_FILE = process.env.DB_FILE || path.join(__dirname, 'data', 'orders.db');
const db = openDb(DB_FILE);

const app = createApp({
  db,
  adminPassword: ADMIN_PASSWORD,
  sessionSecret: SESSION_SECRET,
  webhookSecret: process.env.WEBHOOK_SECRET || '',
  storeName: process.env.STORE_NAME || '',
  storeUrl: process.env.STORE_URL || '',
  secureCookies: IS_PROD,
});

const server = app.listen(PORT, () => {
  console.log(`✅ الموقع شغال: http://localhost:${PORT}`);
  console.log(`   لوحة التحكم: http://localhost:${PORT}/admin`);
  console.log(`   قاعدة البيانات: ${DB_FILE}`);
});

function shutdown() {
  server.close(() => { db.close(); process.exit(0); });
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
