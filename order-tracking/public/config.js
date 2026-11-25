// ============================================================
// إعدادات الموقع — غيّر القيم دي بس
// ============================================================
// القيم دي بتلاقيها في Supabase ← Project Settings ← API Keys (أو Data API)
// المفتاح ده "عام" ومعمول عشان يتحط في الموقع، والداتا محمية بقواعد Row Level Security.
// أوعى تحط هنا مفتاح service_role أو secret أبداً.
window.APP_CONFIG = {
  SUPABASE_URL: 'https://YOUR-PROJECT.supabase.co',
  SUPABASE_KEY: 'YOUR-ANON-OR-PUBLISHABLE-KEY',

  // اسم المتجر ولينكه (بيظهروا في صفحة التتبع)
  STORE_NAME: 'متجري',
  STORE_URL: '',
};
