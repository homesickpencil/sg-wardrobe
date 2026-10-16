-- Wardrobe app: the feedback form on the Settings page.
-- Paste into Supabase → SQL Editor → New query, then click Run. Safe to run again.
-- Read what people sent in Table Editor → feedback.

create table if not exists public.feedback (
  id         bigint generated always as identity primary key,
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade,
  message    text not null check (char_length(message) between 1 and 2000),
  created_at timestamptz not null default now()
);

-- signed-in people can send feedback as themselves, but cannot read anyone's (including their own)
alter table public.feedback enable row level security;
drop policy if exists "send feedback" on public.feedback;
create policy "send feedback" on public.feedback for insert to authenticated with check ((select auth.uid()) = user_id);
revoke all on public.feedback from anon, authenticated;
grant insert (message) on public.feedback to authenticated;
