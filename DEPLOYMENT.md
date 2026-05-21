# Deployment checklist

This file is the practical deployment checklist for getting the project to the point where only the social account logins and API approvals remain.

## 1. Supabase

Create a Supabase project.

Open the SQL editor and run:

```text
supabase/migrations/001_content_queue.sql
```

Create a public storage bucket named:

```text
videos
```

The worker uploads processed vertical videos into this bucket.

## 2. GitHub Actions secrets

Add these repository secrets first:

```text
SUPABASE_URL
SUPABASE_KEY
SUPABASE_SERVICE_KEY
```

The service key is required because the worker writes to tables protected by row level security.

Do not add social posting credentials until the accounts are created and tested.

## 3. Vercel dashboard deployment

Import the GitHub repo into Vercel.

Set these Vercel environment variables:

```text
SUPABASE_URL
SUPABASE_KEY
SUPABASE_SERVICE_KEY
DASHBOARD_PASSWORD
VIDEO_BUCKET
```

`DASHBOARD_PASSWORD` is required in production. Without it, the dashboard will not authenticate.

After deploy, open:

```text
/api/health
```

If you are not logged in, log in first at:

```text
/login
```

## 4. First system test

Run this workflow manually:

```text
Post - Rayan Cherki
```

Then check the dashboard for candidates with status:

```text
found
```

Approve one candidate.

Run the workflow again.

Expected state change:

```text
found -> approved -> processing -> processed
```

If social credentials are missing, the clip should stay `processed` instead of being lost.

## 5. Later social account setup

When the Instagram and TikTok accounts exist, add the social secrets:

```text
CHERKI_IG_USER_ID
CHERKI_IG_ACCESS_TOKEN
BELLINGHAM_IG_USER_ID
BELLINGHAM_IG_ACCESS_TOKEN
YAMAL_IG_USER_ID
YAMAL_IG_ACCESS_TOKEN
TIKTOK_ACCESS_TOKEN
```

Keep TikTok private during testing.

Do not turn on public posting until each account has successfully posted a private test clip.

## 6. Keep auto approval off

For now, keep:

```text
AUTO_APPROVE=false
```

The correct milestone is a reliable review queue, not blind posting.
