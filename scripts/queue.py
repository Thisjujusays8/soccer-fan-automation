#!/usr/bin/env python3
import argparse
import json
import os
import sys
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
    if method in ('POST', 'PATCH'):
        headers['Prefer'] = 'return=representation'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode('utf-8')
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        raise SystemExit(f'Supabase error {exc.code}: {body}')


def list_candidates(status, limit):
    filters = []
    if PLAYER_SLUG:
        filters.append('player_slug=eq.' + urllib.parse.quote(PLAYER_SLUG))
    if status:
        filters.append('status=eq.' + urllib.parse.quote(status))
    filters.append('select=id,player_slug,title,score,status,source_url,video_url,error_message,created_at')
    filters.append('order=created_at.desc')
    filters.append('limit=' + str(limit))
    rows = request_json('clip_candidates', params='&'.join(filters))
    if not rows:
        print('No candidates found.')
        return
    for row in rows:
        print('\n' + row['id'])
        print('  player:', row.get('player_slug'))
        print('  status:', row.get('status'))
        print('  score:', row.get('score'))
        print('  title:', row.get('title'))
        print('  source:', row.get('source_url'))
        if row.get('video_url'):
            print('  video:', row.get('video_url'))
        if row.get('error_message'):
            print('  error:', row.get('error_message'))


def update_status(candidate_id, status):
    rows = request_json('clip_candidates', method='PATCH', params='id=eq.' + urllib.parse.quote(candidate_id), payload={'status': status, 'error_message': None})
    if not rows:
        raise SystemExit('No candidate updated. Check the id.')
    print(f'Updated {candidate_id} to {status}.')


def main():
    require_env()
    parser = argparse.ArgumentParser(description='Manage the soccer content queue.')
    sub = parser.add_subparsers(dest='command', required=True)

    p_list = sub.add_parser('list')
    p_list.add_argument('--status', default='found')
    p_list.add_argument('--limit', type=int, default=20)

    p_approve = sub.add_parser('approve')
    p_approve.add_argument('candidate_id')

    p_reject = sub.add_parser('reject')
    p_reject.add_argument('candidate_id')

    p_reset = sub.add_parser('reset')
    p_reset.add_argument('candidate_id')
    p_reset.add_argument('--status', default='found')

    args = parser.parse_args()
    if args.command == 'list':
        list_candidates(args.status, args.limit)
    elif args.command == 'approve':
        update_status(args.candidate_id, 'approved')
    elif args.command == 'reject':
        update_status(args.candidate_id, 'rejected')
    elif args.command == 'reset':
        update_status(args.candidate_id, args.status)


if __name__ == '__main__':
    main()
