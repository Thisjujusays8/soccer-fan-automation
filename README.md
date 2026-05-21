# soccer-fan-automation

Automated soccer clip discovery, approval, processing, storage, and posting system.

This project should not be a blind reposting bot. The correct architecture is a queue based content pipeline. It should find possible clips, save them for review, let a human approve or reject them, process approved clips into vertical format, upload the processed result, then post only when the social accounts and API credentials are ready.

## Current player runs

The repository already has three GitHub Actions workflows.

| Player | Workflow slug | Account idea |
|---|---|---|
| Rayan Cherki | `cherki` | `cherkiworld` |
| Jude Bellingham | `bellingham` | `bellinghamdaily` |
| Lamine Yamal | `yamal` | `yamalworld` |

These slugs matter because the worker stores every candidate and post by `player_slug`.

## Target architecture

```text
GitHub Actions schedule
        |
        v
scripts/post.py
        |
        v
Discover candidate clips
        |
        v
Save candidates in Supabase
        |
        v
Manual approval or rejection
        |
        v
Process approved clip with ffmpeg
        |
        v
Upload finished vertical video to Supabase Storage
        |
        v
Post to Instagram and TikTok when credentials exist
        |
        v
Save post records and later collect metrics
```

## Why this design

Most content automation systems fail when they try to go straight from search result to public post. The safer design is a queue.

The queue gives you:

1. Duplicate protection
2. Quality control
3. A place to inspect errors
4. A way to avoid bad clips
5. A clean approval step before posting
6. A record of what was already used
7. A future analytics loop

## What each script should do

### `scripts/post.py`

Main worker. It should support four modes.

| Mode | Purpose |
|---|---|
| `discover` | Search YouTube and save new candidates as `found` |
| `process` | Take one `approved` candidate and create a vertical video |
| `post` | Take one `processed` candidate and post it to available platforms |
| `auto` | Run discovery, process one approved candidate, then post one processed candidate |

Important behavior:

- It should never post an unapproved clip when `AUTO_APPROVE=false`.
- It should skip Instagram if Instagram credentials are missing.
- It should skip TikTok if TikTok credentials are missing.
- It should keep a processed clip as `processed` if no platform credentials exist yet.
- It should mark failed clips as `failed` with an error message.
- It should use the exact workflow slugs: `cherki`, `bellingham`, and `yamal`.

### `scripts/queue.py`

Manual queue manager.

It should let you list candidates, approve good ones, reject bad ones, and reset stuck statuses.

Commands:

```bash
python scripts/queue.py list --status found
python scripts/queue.py approve CANDIDATE_ID
python scripts/queue.py reject CANDIDATE_ID
python scripts/queue.py reset CANDIDATE_ID --status found
```

### `.github/workflows/post-cherki.yml`

Scheduled worker for Rayan Cherki.

It should:

- Run on a cron schedule
- Allow manual workflow dispatch
- Install Python, yt-dlp, ffmpeg, and fonts
- Set `PLAYER_SLUG=cherki`
- Run `python scripts/post.py`

### `.github/workflows/post-bellingham.yml`

Scheduled worker for Jude Bellingham.

It should:

- Run on a cron schedule
- Allow manual workflow dispatch
- Install Python, yt-dlp, ffmpeg, and fonts
- Set `PLAYER_SLUG=bellingham`
- Run `python scripts/post.py`

### `.github/workflows/post-yamal.yml`

Scheduled worker for Lamine Yamal.

It should:

- Run on a cron schedule
- Allow manual workflow dispatch
- Install Python, yt-dlp, ffmpeg, and fonts
- Set `PLAYER_SLUG=yamal`
- Run `python scripts/post.py`

## Database tables

### `players`

Stores the three player configurations.

Expected slugs:

```text
cherki
bellingham
yamal
```

### `clip_candidates`

Stores every found clip before posting.

Important statuses:

| Status | Meaning |
|---|---|
| `found` | Candidate found but not approved |
| `approved` | Candidate approved for processing |
| `rejected` | Candidate rejected |
| `processing` | Worker is processing this candidate |
| `processed` | Vertical video is ready |
| `posting` | Worker is trying to post this candidate |
| `posted` | Candidate has been posted |
| `failed` | Something broke and needs review |

### `posts`

Stores platform posting records.

One clip can create more than one post record because it can go to Instagram and TikTok.

### `post_metrics`

Future analytics table.

This should eventually track:

- Views
- Likes
- Comments
- Shares
- Saves
- Collection time

## Setup checklist

### 1. Supabase

Create a Supabase project.

Run this SQL file in the Supabase SQL editor:

```text
supabase/migrations/001_content_queue.sql
```

Create a public storage bucket called:

```text
videos
```

### 2. GitHub secrets

Add the Supabase secrets first:

```text
SUPABASE_URL
SUPABASE_KEY
SUPABASE_SERVICE_KEY
```

Social posting secrets can wait until the accounts exist:

```text
CHERKI_IG_USER_ID
CHERKI_IG_ACCESS_TOKEN
BELLINGHAM_IG_USER_ID
BELLINGHAM_IG_ACCESS_TOKEN
YAMAL_IG_USER_ID
YAMAL_IG_ACCESS_TOKEN
TIKTOK_ACCESS_TOKEN
```

### 3. First safe test

Run one workflow manually from GitHub Actions.

Then check Supabase:

```text
clip_candidates
```

You should see candidates with status:

```text
found
```

### 4. Manual approval test

Approve one clip:

```bash
python scripts/queue.py approve CANDIDATE_ID
```

Run the workflow again.

Expected result:

```text
approved -> processing -> processed
```

If social credentials are missing, the clip should stay `processed` and not be lost.

### 5. Social account setup

Before real public posting, create or connect:

- Instagram professional accounts
- Meta developer app
- TikTok developer app
- TikTok account authorization

Do not set `AUTO_APPROVE=true` until the queue has been tested for several runs.

## Current known gaps

1. The Yamal workflow still needs the same hardening that was applied to Cherki and Bellingham.
2. The web dashboard is only a placeholder.
3. Metrics collection is not implemented yet.
4. Exact duplicate detection only uses source URL hash. It does not detect reposted copies of the same clip from different YouTube uploads.
5. The clip selection system is still title based. It does not yet analyze video content.
6. Copyright and platform policy risk still exists if reposting clips you do not own or have rights to use.

## Next work plan

### Phase 1: Make the backend reliable

- Finish hardening the Yamal workflow.
- Add a workflow validation check.
- Add Python syntax checks in GitHub Actions.
- Add better retry handling for transient YouTube and Supabase failures.
- Add a cleanup path for old failed candidates.

### Phase 2: Make approval usable

- Replace the placeholder dashboard with a real approval UI.
- Show candidates grouped by player.
- Show source link, title, score, status, and processed video preview.
- Add approve and reject buttons.
- Add reset failed candidate button.

### Phase 3: Make posting safer

- Keep Instagram and TikTok disabled until credentials are confirmed.
- Add account specific secrets for each Instagram page.
- Keep TikTok privacy as `SELF_ONLY` for testing.
- Only switch to public posting after several successful private tests.

### Phase 4: Add analytics

- Pull views, likes, comments, shares, and saves.
- Calculate performance by player and search query.
- Feed that data back into candidate scoring.

### Phase 5: Improve clip quality

- Add better scoring rules.
- Use duration and upload metadata.
- Penalize old, low quality, compilation, podcast, reaction, and gameplay results.
- Eventually add scene detection or transcript based filtering.

## Operating rule

The system should prioritize reliability over speed.

The correct first milestone is not automatic posting. The correct first milestone is:

```text
Three scheduled workflows reliably filling a review queue with non duplicate candidate clips.
```

Only after that should posting be enabled.
