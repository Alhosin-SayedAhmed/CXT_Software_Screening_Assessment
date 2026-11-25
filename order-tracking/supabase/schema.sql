-- جداول موقع تتبع الطلبات على Supabase.
-- السيرفر بيشغّل الملف ده لوحده أول ما يقوم، فمش لازم تعمل حاجة.
-- ولو حابب تشغّله بإيدك: Supabase ← SQL Editor ← الصق الملف ← Run.
-- الملف آمن لو اتشغّل أكتر من مرة.

create table if not exists public.orders (
  id            integer generated always as identity primary key,
  order_number  text not null unique,
  customer_name text not null default '',
  phone         text not null default '',
  product       text not null default '',
  note          text not null default '',
  stage         text not null default 'received',
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

-- سجل بكل مرحلة الطلب دخلها وإمتى
create table if not exists public.stage_history (
  id         bigint generated always as identity primary key,
  order_id   integer not null references public.orders(id) on delete cascade,
  stage      text not null,
  changed_at timestamptz not null default now()
);

create index if not exists stage_history_order_id_idx on public.stage_history (order_id);
create index if not exists orders_updated_at_idx on public.orders (updated_at desc);

-- بيحدّث updated_at أوتوماتيك مع أي تعديل
create or replace function public.orders_set_updated_at()
returns trigger language plpgsql set search_path = '' as $$
begin
  new.updated_at := now();
  return new;
end $$;

-- بيسجّل المرحلة في stage_history مع أي إضافة أو تغيير مرحلة،
-- حتى لو غيّرتها بإيدك من Table Editor في Supabase
create or replace function public.orders_log_stage()
returns trigger language plpgsql set search_path = '' as $$
begin
  if tg_op = 'INSERT' or new.stage is distinct from old.stage then
    insert into public.stage_history (order_id, stage, changed_at)
    values (new.id, new.stage, now());
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

-- حماية: مفيش حد يقدر يقرا أو يعدّل الجداول بمفاتيح Supabase العامة (anon).
-- السيرفر بتاعنا بيتصل بحساب الداتابيس نفسه، فمش بيتأثر بالحماية دي.
alter table public.orders enable row level security;
alter table public.stage_history enable row level security;
