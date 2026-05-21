create extension if not exists pgcrypto;

create table if not exists public.players (
    id uuid primary key default gen_random_uuid(),
    slug text unique not null,
    player_name text not null,
    search_query text not null,
    watermark_handle text not null,
    active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.clip_candidates (
    id uuid primary key default gen_random_uuid(),
    player_slug text not null,
    source_url text not null,
    source_video_id text,
    source_hash text not null unique,
    title text not null,
    normalized_title text,
    score integer not null default 0,
    status text not null default 'found' check (
        status in ('found','approved','rejected','processing','processed','posting','posted','failed')
    ),
    video_url text,
    video_size_bytes bigint,
    metadata jsonb not null default '{}'::jsonb,
    error_message text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    processed_at timestamptz,
    posted_at timestamptz
);

create table if not exists public.posts (
    id uuid primary key default gen_random_uuid(),
    clip_candidate_id uuid references public.clip_candidates(id) on delete set null,
    player_slug text not null,
    source_url text not null,
    source_video_id text,
    source_hash text,
    normalized_title text,
    video_url text not null,
    video_size_bytes bigint,
    title text not null,
    platform text not null default 'manual',
    platform_post_id text,
    ig_post_id text,
    tt_post_id text,
    status text not null default 'posted',
    created_at timestamptz not null default now()
);

create table if not exists public.post_metrics (
    id uuid primary key default gen_random_uuid(),
    post_id uuid not null references public.posts(id) on delete cascade,
    views integer,
    likes integer,
    comments integer,
    shares integer,
    saves integer,
    collected_at timestamptz not null default now()
);

insert into public.players (slug, player_name, search_query, watermark_handle)
values
    ('cherki', 'Rayan Cherki', 'Rayan Cherki highlights goals assists skills 2025', 'cherkiworld'),
    ('bellingham', 'Jude Bellingham', 'Jude Bellingham highlights goals assists Real Madrid England 2025', 'bellinghamdaily'),
    ('yamal', 'Lamine Yamal', 'Lamine Yamal highlights goals assists Barcelona Spain 2025', 'yamalworld')
on conflict (slug) do update set
    player_name = excluded.player_name,
    search_query = excluded.search_query,
    watermark_handle = excluded.watermark_handle,
    active = true,
    updated_at = now();

create index if not exists idx_clip_candidates_player_status_score
    on public.clip_candidates(player_slug, status, score desc, created_at asc);

create index if not exists idx_clip_candidates_source_video_id
    on public.clip_candidates(source_video_id);

create index if not exists idx_clip_candidates_player_normalized_title
    on public.clip_candidates(player_slug, normalized_title)
    where normalized_title is not null;

create index if not exists idx_posts_player_platform_created
    on public.posts(player_slug, platform, created_at desc);

create unique index if not exists idx_posts_source_platform_unique
    on public.posts(source_hash, platform)
    where source_hash is not null;

create index if not exists idx_posts_player_normalized_title
    on public.posts(player_slug, normalized_title)
    where normalized_title is not null;

create or replace function public.set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists set_players_updated_at on public.players;
create trigger set_players_updated_at
before update on public.players
for each row
execute function public.set_updated_at();

drop trigger if exists set_clip_candidates_updated_at on public.clip_candidates;
create trigger set_clip_candidates_updated_at
before update on public.clip_candidates
for each row
execute function public.set_updated_at();

alter table public.players enable row level security;
alter table public.clip_candidates enable row level security;
alter table public.posts enable row level security;
alter table public.post_metrics enable row level security;

drop policy if exists "service role full access to players" on public.players;
create policy "service role full access to players"
    on public.players for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

drop policy if exists "service role full access to clip_candidates" on public.clip_candidates;
create policy "service role full access to clip_candidates"
    on public.clip_candidates for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

drop policy if exists "service role full access to posts" on public.posts;
create policy "service role full access to posts"
    on public.posts for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

drop policy if exists "service role full access to post_metrics" on public.post_metrics;
create policy "service role full access to post_metrics"
    on public.post_metrics for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');
