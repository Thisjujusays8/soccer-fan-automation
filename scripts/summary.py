#!/usr/bin/env python3
import json
import os
import urllib.error
import urllib.parse
import urllib.request

SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_KEY', '')
PLAYER_SLUG = os.environ.get('PLAYER_SLUG', '')

STATUSES = ['found', 'approved', 'rejected', 'processing', 'processed', 'posting', 'posted', 'failed']


def require_env():
    missing = []
    if not SUPABASE_URL:
        missing.append('SUPABASE_URL')
    if not SUPABASE_KEY:
        missing.append('SUPABASE_SERVICE_KEY or SUPABASE_KEY')
    if missing:
        raise SystemExit('Missing environment variables: ' + ', '.join(missing))


def get_rows():
    filters = []
    if PLAYER_SLUG:
        filters.append('player_slug=eq.' + urllib.parse.quote(PLAYER_SLUG))
    filters.append('select=player_slug,status')
    url = f'{SUPABASE_URL}/rest/v1/clip_candidates?' + '&'.join(filters)
    req = urllib.request.Request(url, headers={
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        raise SystemExit(f'Supabase error {exc.code}: {body}')


def main():
    require_env()
    rows = get_rows()
    counts = {}
    for row in rows:
        key = (row.get('player_slug') or 'unknown', row.get('status') or 'unknown')
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        print('No candidates found.')
        return
    players = sorted(set(player for player, _status in counts))
    for player in players:
        print('\n' + player)
        for status in STATUSES:
            count = counts.get((player, status), 0)
            if count:
                print(f'  {status}: {count}')


if __name__ == '__main__':
    main()
