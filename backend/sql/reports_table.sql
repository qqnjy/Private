-- AI weekly report cache. One row per brand + week.
-- Re-running generation for the same brand+week returns the cached outline+slides
-- instead of hitting the LLM, unless refresh=true is passed.

create table if not exists reports (
  brand_name text not null,
  week_start date not null,
  week_end date not null,
  outline text not null,
  slides jsonb not null default '{}'::jsonb,
  notes text,
  generated_at timestamptz not null default now(),
  primary key (brand_name, week_start, week_end)
);

create index if not exists reports_generated_at_idx on reports (generated_at desc);

alter table reports enable row level security;
drop policy if exists "reports all" on reports;
create policy "reports all" on reports for all using (true) with check (true);
