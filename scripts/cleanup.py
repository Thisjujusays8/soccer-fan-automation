#!/usr/bin/env python3
import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request

SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_KEY', '')
PLAYER_SLUG = os.environ.get('PLAYER_SLUG', '')

HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json',
}


def require_env():
    missing = []
    if not SUPABASE_URL:
        missing.append('SUPABASE_URL')
    if not SUPABASE_KEY:
        missing.append('SUPABASE_SERVICE_KEY or SUPABASE_KEY')
    if missing:
        raise SystemExit('Missing environment variables: ' + ', '.join(missing))


def request_json(path, method='GET', params='', payload=None):
    url = f'{SUPABASE_URL}/rest/v1/{path}'
    if params:
        url += '?' + params
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    headers = dict(HEADERS)
    if method == 'PATCH':
        headers['Prefer'] = 'return=representation'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode('utf-8')
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        raise SystemExit(f'Supabase error {exc.code}: {body}')


def list_rows(status, limit):
    filters = ['status=eq.' + urllib.parse.quote(status)]
    if PLAYER_SLUG:
        filters.append('player_slug=eq.' + urllib.parse.quote(PLAYER_SLUG))
    filters.append('select=id,player_slug,status,title,created_at,error_message')
    filters.append('order=created_at.asc')
    filters.append('limit=' + str(limit))
    rows = request_json('clip_candidates', params='&'.join(filters))
    if not rows:
        print('No matching candidates.')
        return []
    for row in rows:
        print('\n' + row['id'])
        print('  player:', row.get('player_slug'))
        print('  status:', row.get('status'))
        print('  created:', row.get('created_at'))
        print('  title:', row.get('title'))
        if row.get('error_message'):
            print('  error:', row.get('error_message'))
    return rows


def reset_failed(limit):
    rows = list_rows('failed', limit)
    if not rows:
        return
    ids = ','.join(row['id'] for row in rows)
    params = 'id=in.(' + ids + ')'
    request_json('clip_candidates', method='PATCH', params=params, payload={'status': 'found', 'error_message': None})
    print('\nReset', len(rows), 'failed candidate(s) to found.')


def main():
    require_env()
    parser = argparse.ArgumentParser(description='Inspect or reset failed and rejected clip candidates without deleting data.')
    parser.add_argument('action', choices=['list-failed', 'list-rejected', 'reset-failed'])
    parser.add_argument('--limit', type=int, default=25)
    args = parser.parse_args()

    if args.action == 'list-failed':
        list_rows('failed', args.limit)
    elif args.action == 'list-rejected':
        list_rows('rejected', args.limit)
    elif args.action == 'reset-failed':
        reset_failed(args.limit)


if __name__ == '__main__':
    main()
