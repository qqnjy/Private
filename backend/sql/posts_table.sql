-- Run this once in Supabase SQL Editor to create the posts cache table.

create table if not exists posts (
  id text primary key,
  brand_name text not null,
  platform text not null check (platform in ('fb', 'ig')),
  message text,
  permalink text,
  media_type text,
  media_url text,
  created_at timestamptz,
  metrics jsonb not null default '{}'::jsonb,
  week_start date not null,
  week_end date not null,
  fetched_at timestamptz not null default now()
);

create index if not exists posts_brand_week_idx on posts (brand_name, week_start, week_end);
create index if not exists posts_created_at_idx on posts (created_at desc);

-- Allow anon key (the backend uses SUPABASE_ANON_KEY) to read/write this table.
-- If RLS is enabled on the schema, you'll need policies; the simplest is:
alter table posts enable row level security;

drop policy if exists "posts select all" on posts;
create policy "posts select all" on posts for select using (true);

drop policy if exists "posts insert all" on posts;
create policy "posts insert all" on posts for insert with check (true);

drop policy if exists "posts update all" on posts;
create policy "posts update all" on posts for update using (true) with check (true);
