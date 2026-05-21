# Local testing

Use this when you want to test the worker or dashboard from your laptop.

## 1. Python worker test

Install requirements:

```bash
python -m pip install -r requirements.txt
```

Required tools:

```text
ffmpeg
ffprobe
yt-dlp
```

Set environment variables locally. At minimum:

```text
SUPABASE_URL
SUPABASE_KEY
SUPABASE_SERVICE_KEY
PLAYER_SLUG
SEARCH_QUERY
WATERMARK_HANDLE
```

Safe discovery test:

```bash
MODE=discover POST_TO_IG=false POST_TO_TIKTOK=false python scripts/post.py
```

Queue summary:

```bash
python scripts/summary.py
```

List found candidates:

```bash
python scripts/queue.py list --status found
```

Approve a candidate:

```bash
python scripts/queue.py approve CANDIDATE_ID
```

Process approved candidate:

```bash
MODE=process POST_TO_IG=false POST_TO_TIKTOK=false python scripts/post.py
```

## 2. Dashboard test

Install dependencies:

```bash
npm install
```

Run locally:

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

In local development, the dashboard can run without `DASHBOARD_PASSWORD`.

In production, `DASHBOARD_PASSWORD` is required.

## 3. Health check

After logging in, open:

```text
/api/health
```

Expected result:

```text
ok: true
```

If it is false, fix the missing Supabase variables or run the migration.

## 4. Validation

Run:

```bash
python scripts/validate_project.py
```

This checks the repo contract before deploying.
