CREATE TABLE IF NOT EXISTS players (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  ig_handle TEXT,
  tt_handle TEXT,
  search_query TEXT NOT NULL,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS posts (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  player_slug TEXT NOT NULL,
  source_url TEXT NOT NULL,
  video_url TEXT,
  ig_post_id TEXT,
  tt_post_id TEXT,
  title TEXT,
  posted_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(player_slug, source_url)
);

CREATE INDEX IF NOT EXISTS posts_player_slug_idx ON posts(player_slug);
CREATE INDEX IF NOT EXISTS posts_source_url_idx ON posts(source_url);

INSERT INTO players (slug, display_name, ig_handle, tt_handle, search_query) VALUES
  ('cherki','Ryan Cherki','cherkiworld','cherkiworld','Ryan Cherki highlights goals 2025'),
  ('yamal','Lamine Yamal','yamalworld','yamalworld','Lamine Yamal highlights goals 2025'),
  ('bellingham','Jude Bellingham','bellinghamdaily','bellinghamdaily','Jude Bellingham highlights goals 2025')
ON CONFLICT (slug) DO NOTHING;
