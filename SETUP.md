# Setup

This repo has three GitHub Actions runs:

- Rayan Cherki uses slug cherki
- Jude Bellingham uses slug bellingham
- Lamine Yamal uses slug yamal

## Supabase

Create a Supabase project.

Run the SQL file in `supabase/migrations/001_content_queue.sql` from the Supabase SQL editor.

Create a public storage bucket named `videos`.

## First test

Run one workflow manually from GitHub Actions.

Then check the `clip_candidates` table in Supabase.

Candidates start as `found`.

To test processing, change one candidate status to `approved` and run the workflow again.

## Social posting

Instagram and TikTok posting will not work until the social developer accounts and tokens are created.

Keep auto approval off until the queue is tested.
