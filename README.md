# soccer-fan-automation

Automated soccer clip discovery, processing, approval, and posting system.

## Current runs

The repo has three GitHub Actions workflows:

- Rayan Cherki: `cherki`
- Jude Bellingham: `bellingham`
- Lamine Yamal: `yamal`

## What it does

1. Searches for player highlight videos.
2. Saves candidates into Supabase.
3. Lets you approve or reject candidates.
4. Processes approved clips into vertical videos.
5. Uploads processed clips to Supabase Storage.
6. Posts to Instagram and TikTok once account credentials exist.
7. Tracks posted clips and basic metrics.

## First setup

1. Create a Supabase project.
2. Run `supabase/migrations/001_content_queue.sql` in the Supabase SQL editor.
3. Create a public storage bucket named `videos`.
4. Add the required GitHub repository secrets.
5. Run one GitHub Action manually.
6. Check the `clip_candidates` table.

## Queue commands

List found candidates:

```bash
python scripts/queue.py list --status found
```

Approve a candidate:

```bash
python scripts/queue.py approve CANDIDATE_ID
```

Reject a candidate:

```bash
python scripts/queue.py reject CANDIDATE_ID
```

Process and post happens through `scripts/post.py` from GitHub Actions.

Keep `AUTO_APPROVE=false` until the queue is tested.
