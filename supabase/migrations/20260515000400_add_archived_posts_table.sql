-- Archive deleted posts for moderation/audit history.
-- Rows are retained for 90 days and are intended to be removed by app-side cleanup.

create table if not exists public.archived_posts (
  id uuid primary key default gen_random_uuid(),
  original_post_id uuid not null,
  post_owner_id uuid,
  deleted_by uuid,
  deleted_by_role text,
  deletion_source text not null default 'admin',
  delete_reason text,
  delete_note text,
  archived_payload jsonb not null default '{}'::jsonb,
  archived_at timestamptz not null default timezone('utc', now()),
  purge_after timestamptz not null default (timezone('utc', now()) + interval '90 days')
);

create index if not exists idx_archived_posts_original_post_id on public.archived_posts(original_post_id);
create index if not exists idx_archived_posts_purge_after on public.archived_posts(purge_after);
create index if not exists idx_archived_posts_archived_at on public.archived_posts(archived_at desc);

alter table public.archived_posts enable row level security;

drop policy if exists "Service role full access archived_posts" on public.archived_posts;
create policy "Service role full access archived_posts"
on public.archived_posts
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');
