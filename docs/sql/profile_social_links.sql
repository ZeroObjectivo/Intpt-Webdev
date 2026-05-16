create table if not exists public.profile_social_links (
    id uuid primary key default gen_random_uuid(),
    profile_id uuid not null references public.profiles(id) on delete cascade,
    platform text not null check (platform in ('facebook', 'instagram', 'tiktok', 'linkedin', 'discord')),
    url text not null,
    visibility text not null default 'public' check (visibility in ('public', 'only_me')),
    position integer not null check (position between 1 and 3),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists profile_social_links_profile_position_idx
    on public.profile_social_links (profile_id, position);

create unique index if not exists profile_social_links_profile_url_idx
    on public.profile_social_links (profile_id, url);

create index if not exists profile_social_links_profile_id_idx
    on public.profile_social_links (profile_id);

create or replace trigger set_updated_at_profile_social_links
    before update on public.profile_social_links
    for each row execute function public.handle_updated_at();

alter table public.profile_social_links enable row level security;

create policy "Social links are viewable by everyone"
    on public.profile_social_links
    for select
    using (true);

create policy "Users can insert their own social links"
    on public.profile_social_links
    for insert
    with check (auth.uid() = profile_id);

create policy "Users can update their own social links"
    on public.profile_social_links
    for update
    using (auth.uid() = profile_id);

create policy "Users can delete their own social links"
    on public.profile_social_links
    for delete
    using (auth.uid() = profile_id);
