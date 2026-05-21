alter table public.clip_candidates
    add column if not exists normalized_title text;

alter table public.clip_candidates
    add column if not exists video_size_bytes bigint;

alter table public.posts
    add column if not exists normalized_title text;

alter table public.posts
    add column if not exists video_size_bytes bigint;

create index if not exists idx_clip_candidates_player_normalized_title
    on public.clip_candidates(player_slug, normalized_title)
    where normalized_title is not null;

create index if not exists idx_posts_player_normalized_title
    on public.posts(player_slug, normalized_title)
    where normalized_title is not null;
