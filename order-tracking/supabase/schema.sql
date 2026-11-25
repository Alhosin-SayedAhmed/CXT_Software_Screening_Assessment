-- ============================================================
-- موقع تتبع الطلبات — إعداد Supabase
-- شغّل الملف ده مرة واحدة: Supabase ← SQL Editor ← New query ← الصق ← Run
-- آمن لو اتشغّل أكتر من مرة (مش بيمسح بيانات).
-- ============================================================

-- ---------- المراحل ----------
-- تقدر تعدّل الأسماء والوصف والترتيب من Table Editor ← stages
-- icon: clipboard, box, gear, shield, package, truck, home, check
create table if not exists public.stages (
  key         text primary key,
  position    integer not null,
  label       text not null,
  description text not null default '',
  icon        text not null default 'dot'
);

insert into public.stages (key, position, label, description, icon) values
  ('received',      1, 'تم استلام الطلب', 'وصلنا طلبك وتم تأكيده',        'clipboard'),
  ('preparing',     2, 'جاري التجهيز',    'بنجهز الخامات والمكونات',      'box'),
  ('manufacturing', 3, 'جاري التصنيع',    'طلبك على خط التصنيع دلوقتي',   'gear'),
  ('quality',       4, 'فحص الجودة',      'بنختبر المنتج قبل التغليف',    'shield'),
  ('completed',     5, 'تم الانتهاء',     'المنتج جاهز ومتغلف',           'package'),
  ('shipping',      6, 'جاري الشحن',      'الطلب مع شركة الشحن',          'truck'),
  ('delivered',     7, 'تم التوصيل',      'وصل الطلب للعميل',             'home')
on conflict (key) do nothing;

-- ---------- الطلبات ----------
create table if not exists public.orders (
  id            integer generated always as identity primary key,
  order_number  text not null unique check (length(order_number) between 1 and 50),
  customer_name text not null default '' check (length(customer_name) <= 100),
  phone         text not null default '' check (length(phone) <= 30),
  product       text not null default '' check (length(product) <= 200),
  note          text not null default '' check (length(note) <= 500),
  stage         text not null default 'received' references public.stages (key) on update cascade,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

-- سجل بكل مرحلة الطلب دخلها وإمتى (بيتملي أوتوماتيك)
create table if not exists public.stage_history (
  id         bigint generated always as identity primary key,
  order_id   integer not null references public.orders (id) on delete cascade,
  stage      text not null,
  changed_at timestamptz not null default now()
);

create index if not exists stage_history_order_id_idx on public.stage_history (order_id);
create index if not exists orders_updated_at_idx on public.orders (updated_at desc);

-- ---------- الأدمن ----------
-- مين مسموح له يدخل لوحة التحكم. ضيف نفسك بالسطر اللي في آخر الملف.
create table if not exists public.admins (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  created_at timestamptz not null default now()
);

create or replace function public.is_admin()
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.admins where user_id = auth.uid());
$$;

-- ---------- التحديث الأوتوماتيك ----------
create or replace function public.orders_set_updated_at()
returns trigger language plpgsql set search_path = '' as $$
begin
  new.updated_at := now();
  return new;
end $$;

-- بيسجّل المرحلة مع أي إضافة أو تغيير مرحلة — حتى لو من Table Editor
create or replace function public.orders_log_stage()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if tg_op = 'INSERT' or new.stage is distinct from old.stage then
    insert into public.stage_history (order_id, stage, changed_at) values (new.id, new.stage, now());
  end if;
  return new;
end $$;

drop trigger if exists orders_set_updated_at on public.orders;
create trigger orders_set_updated_at
  before update on public.orders
  for each row execute function public.orders_set_updated_at();

drop trigger if exists orders_log_stage on public.orders;
create trigger orders_log_stage
  after insert or update of stage on public.orders
  for each row execute function public.orders_log_stage();

-- ---------- صفحة العميل ----------
-- العميل مش بيقدر يقرا جدول الطلبات. بيسأل عن رقم طلب واحد بس،
-- وبيرجعله حالة الطلب من غير اسم أو تليفون.
create or replace function public.track_order(p_order_number text)
returns json language sql stable security definer set search_path = '' as $$
  select json_build_object(
    'order_number', o.order_number,
    'product',      o.product,
    'note',         o.note,
    'stage',        o.stage,
    'updated_at',   o.updated_at,
    'history', coalesce((
      select json_agg(json_build_object('stage', h.stage, 'changed_at', h.changed_at) order by h.id)
      from public.stage_history h where h.order_id = o.id
    ), '[]'::json)
  )
  from public.orders o
  where o.order_number = left(regexp_replace(btrim(coalesce(p_order_number, '')), '^#', ''), 50);
$$;

-- ---------- لوحة التحكم ----------
-- الدوال دي بتشتغل بصلاحيات اللي مسجّل دخول، فغير الأدمن مش هيشوف حاجة.
create or replace function public.admin_list_orders(p_search text default '', p_stage text default '')
returns setof public.orders language sql stable set search_path = '' as $$
  select o.* from public.orders o
  where (coalesce(p_search, '') = ''
         or o.order_number  ilike '%' || replace(replace(replace(p_search, '\', '\\'), '%', '\%'), '_', '\_') || '%'
         or o.customer_name ilike '%' || replace(replace(replace(p_search, '\', '\\'), '%', '\%'), '_', '\_') || '%'
         or o.phone         ilike '%' || replace(replace(replace(p_search, '\', '\\'), '%', '\%'), '_', '\_') || '%')
    and (coalesce(p_stage, '') = '' or o.stage = p_stage)
  order by o.updated_at desc, o.id desc
  limit 500;
$$;

create or replace function public.admin_order_counts()
returns table (stage text, n integer) language sql stable set search_path = '' as $$
  select o.stage, count(*)::integer from public.orders o group by o.stage;
$$;

-- ---------- الصلاحيات والحماية (Row Level Security) ----------
alter table public.stages        enable row level security;
alter table public.orders        enable row level security;
alter table public.stage_history enable row level security;
alter table public.admins        enable row level security;

-- الزوار (anon) مالهمش أي وصول مباشر للطلبات
revoke all on public.orders, public.stage_history, public.admins from anon;

drop policy if exists "everyone can read stages" on public.stages;
create policy "everyone can read stages" on public.stages
  for select to anon, authenticated using (true);

drop policy if exists "admins manage stages" on public.stages;
create policy "admins manage stages" on public.stages
  for all to authenticated using (public.is_admin()) with check (public.is_admin());

drop policy if exists "admins manage orders" on public.orders;
create policy "admins manage orders" on public.orders
  for all to authenticated using (public.is_admin()) with check (public.is_admin());

drop policy if exists "admins read history" on public.stage_history;
create policy "admins read history" on public.stage_history
  for select to authenticated using (public.is_admin());

drop policy if exists "users see own admin row" on public.admins;
create policy "users see own admin row" on public.admins
  for select to authenticated using (user_id = auth.uid());

revoke execute on function public.admin_list_orders(text, text) from public, anon;
revoke execute on function public.admin_order_counts() from public, anon;
grant execute on function public.admin_list_orders(text, text) to authenticated;
grant execute on function public.admin_order_counts() to authenticated;
grant execute on function public.track_order(text) to anon, authenticated;
grant execute on function public.is_admin() to anon, authenticated;

-- ============================================================
-- آخر خطوة: خلي حسابك أدمن
-- 1) Authentication ← Users ← Add user ← اكتب إيميلك وباسورد ← فعّل Auto Confirm
-- 2) شغّل السطر ده بعد ما تكتب إيميلك مكان you@example.com:
--
-- insert into public.admins (user_id) select id from auth.users where email = 'you@example.com';
-- ============================================================
