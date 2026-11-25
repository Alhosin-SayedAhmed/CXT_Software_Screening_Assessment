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

const DATABASE_URL = process.env.DATABASE_URL;
if (!DATABASE_URL) {
  console.error('❌ لازم تحط DATABASE_URL (رابط داتابيس Supabase) في ملف .env أو في إعدادات الاستضافة.');
  process.exit(1);
}
const db = openDb(DATABASE_URL);

const app = createApp({
  db,
  adminPassword: ADMIN_PASSWORD,
  sessionSecret: SESSION_SECRET,
  webhookSecret: process.env.WEBHOOK_SECRET || '',
  storeName: process.env.STORE_NAME || '',
  storeUrl: process.env.STORE_URL || '',
  secureCookies: IS_PROD,
});

let server;
db.init()
  .then(() => {
    server = app.listen(PORT, () => {
      console.log(`✅ الموقع شغال: http://localhost:${PORT}`);
      console.log(`   لوحة التحكم: http://localhost:${PORT}/admin`);
      console.log('   قاعدة البيانات: Supabase (متصل)');
    });
  })
  .catch((err) => {
    console.error('❌ مش قادر يتصل بـ Supabase. اتأكد من DATABASE_URL والباسورد.');
    console.error('   ' + err.message);
    process.exit(1);
  });

function shutdown() {
  const done = () => db.close().finally(() => process.exit(0));
  if (server) server.close(done); else done();
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
