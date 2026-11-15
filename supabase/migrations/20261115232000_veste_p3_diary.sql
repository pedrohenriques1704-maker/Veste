-- Personal style diary: independent of closet revisions. Photos stay in the
-- existing private veste-photos bucket, under a per-user diary subdirectory.
create table public.veste_style_diary (
  user_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
  worn_on date not null,
  look_key text not null check (length(look_key) between 1 and 600 and look_key ~ '^[A-Za-z0-9_|-]+$'),
  photo_path text,
  note text not null default '' check (length(note) <= 500),
  rating smallint not null default 0 check (rating between 0 and 5),
  updated_at timestamptz not null default now(),
  primary key(user_id,worn_on,look_key),
  constraint veste_diary_own_photo check (photo_path is null or (photo_path like user_id::text || '/diary/%' and photo_path ~ '^[0-9a-f-]{36}/diary/[0-9a-f-]{36}[.]jpg$'))
);
alter table public.veste_style_diary enable row level security;
revoke all on public.veste_style_diary from public, anon, authenticated;
grant select, insert, update, delete on public.veste_style_diary to authenticated;
create policy veste_diary_read_own on public.veste_style_diary for select to authenticated using (user_id = (select auth.uid()));
create policy veste_diary_insert_own on public.veste_style_diary for insert to authenticated with check (user_id = (select auth.uid()));
create policy veste_diary_update_own on public.veste_style_diary for update to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy veste_diary_delete_own on public.veste_style_diary for delete to authenticated using (user_id = (select auth.uid()));
