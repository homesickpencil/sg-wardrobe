-- Wardrobe app: database, photo storage and privacy rules.
-- Paste all of this into Supabase → SQL Editor → New query, then click Run.
-- Safe to run again: it skips what already exists.

-- ---- Closet items: one row per piece of clothing
create table if not exists public.items (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade,
  name       text not null check (char_length(name) between 1 and 80),
  cat        text not null check (cat in ('Tops', 'Bottoms', 'Dresses', 'Layers', 'Footwear', 'Accessories')),
  fab        text not null check (fab in ('Linen', 'Cotton', 'Viscose', 'Synthetic', 'Wool', 'Denim', 'Leather', 'Other')),
  br         smallint not null default 0 check (br between 0 and 5),
  formality  text not null default 'Casual' check (formality in ('Casual', 'Smart casual', 'Formal')),
  rain       boolean not null default false,
  aircon     boolean not null default false,
  colour     text not null default '' check (char_length(colour) <= 24),
  photo_path text not null check (char_length(photo_path) <= 200),
  position   integer not null default 0,
  created_at timestamptz not null default now()
);
create index if not exists items_user_position on public.items (user_id, position);

-- ---- Everything else one person saves: measurements, removed built-in pieces, latest review
create table if not exists public.user_state (
  user_id      uuid primary key default auth.uid() references auth.users (id) on delete cascade,
  measurements jsonb check (octet_length(measurements::text) < 20000),
  removed      jsonb not null default '[]' check (octet_length(removed::text) < 20000),
  review       jsonb check (octet_length(review::text) < 100000),
  updated_at   timestamptz not null default now()
);

-- ---- Privacy rules: a signed-in person can only see and change their own rows
alter table public.items enable row level security;
alter table public.user_state enable row level security;

drop policy if exists "own items: read" on public.items;
drop policy if exists "own items: add" on public.items;
drop policy if exists "own items: change" on public.items;
drop policy if exists "own items: delete" on public.items;
create policy "own items: read"   on public.items for select to authenticated using ((select auth.uid()) = user_id);
create policy "own items: add"    on public.items for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "own items: change" on public.items for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "own items: delete" on public.items for delete to authenticated using ((select auth.uid()) = user_id);

drop policy if exists "own state: read" on public.user_state;
drop policy if exists "own state: add" on public.user_state;
drop policy if exists "own state: change" on public.user_state;
create policy "own state: read"   on public.user_state for select to authenticated using ((select auth.uid()) = user_id);
create policy "own state: add"    on public.user_state for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "own state: change" on public.user_state for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

-- signed-out visitors get nothing; signed-in people get only what the rules above allow
revoke all on public.items, public.user_state from anon;
grant select, insert, update, delete on public.items to authenticated;
grant select, insert, update on public.user_state to authenticated;

-- ---- Photo storage: a private bucket, JPEG only, at most 500 KB per photo,
-- each person's photos in a folder named after their user id
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('closet-photos', 'closet-photos', false, 524288, array['image/jpeg'])
on conflict (id) do update set public = false, file_size_limit = 524288, allowed_mime_types = array['image/jpeg'];

drop policy if exists "own photos: read" on storage.objects;
drop policy if exists "own photos: add" on storage.objects;
drop policy if exists "own photos: change" on storage.objects;
drop policy if exists "own photos: delete" on storage.objects;
create policy "own photos: read"   on storage.objects for select to authenticated
  using (bucket_id = 'closet-photos' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy "own photos: add"    on storage.objects for insert to authenticated
  with check (bucket_id = 'closet-photos' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy "own photos: change" on storage.objects for update to authenticated
  using (bucket_id = 'closet-photos' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy "own photos: delete" on storage.objects for delete to authenticated
  using (bucket_id = 'closet-photos' and (storage.foldername(name))[1] = (select auth.uid())::text);

-- ---- "Delete my account and data". The app removes the person's photos first (storage only
-- allows that through its own API), then calls this; their items and saved state go with the account.
create or replace function public.delete_my_account()
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  if auth.uid() is null then
    raise exception 'not signed in';
  end if;
  delete from auth.users where id = auth.uid();
end;
$$;
revoke execute on function public.delete_my_account() from public, anon;
grant execute on function public.delete_my_account() to authenticated;
