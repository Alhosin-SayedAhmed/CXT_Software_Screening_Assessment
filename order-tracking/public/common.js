// الاتصال بـ Supabase — بيستخدمه صفحة العميل ولوحة التحكم
(() => {
  const cfg = window.APP_CONFIG || {};
  const configured =
    /^https:\/\/.+/.test(cfg.SUPABASE_URL || '') &&
    !String(cfg.SUPABASE_URL).includes('YOUR-PROJECT') &&
    cfg.SUPABASE_KEY && !String(cfg.SUPABASE_KEY).startsWith('YOUR-');

  window.APP = {
    cfg,
    configured,
    db: configured ? window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_KEY) : null,
    notConfiguredMessage: 'الموقع لسه مش متوصل بـ Supabase. افتح ملف public/config.js وحط SUPABASE_URL و SUPABASE_KEY.',
  };
})();
