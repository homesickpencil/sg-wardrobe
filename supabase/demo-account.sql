-- Wardrobe app: which accounts start with the built-in sample closet.
-- Everyone else starts with an empty closet and the getting-started steps.
-- Paste into Supabase → SQL Editor → New query, then click Run. Safe to run again.

alter table public.user_state add column if not exists demo boolean not null default false;

-- people can save their own state, but cannot turn the sample closet on for themselves
revoke insert, update on public.user_state from authenticated;
grant insert (user_id, measurements, removed, review, updated_at) on public.user_state to authenticated;
grant update (user_id, measurements, removed, review, updated_at) on public.user_state to authenticated;

-- the demo account: replace YOUR-PIN with the demo account's PIN (initials + last 4 phone digits, e.g. SL1234).
-- Sign in once with that PIN first, so the account exists.
insert into public.user_state (user_id, demo)
select id, true from auth.users where email = lower('YOUR-PIN') || '@pin.wardrobe.invalid'
on conflict (user_id) do update set demo = true;

-- check: the demo account should be listed here with demo = true
select upper(split_part(u.email, '@', 1)) as pin, s.demo from auth.users u join public.user_state s on s.user_id = u.id where s.demo;
