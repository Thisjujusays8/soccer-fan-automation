#!/usr/bin/env python3
"""
Metrics scaffolding.

This script is intentionally conservative. It does not call Instagram or TikTok APIs yet.
For now it lists posts that need metrics collection and can insert placeholder metric rows
for local pipeline testing.
"""

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


def request_json(path, method='GET', params='', payload=None, prefer='return=representation'):
    url = f'{SUPABASE_URL}/rest/v1/{path}'
    if params:
        url += '?' + params
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    headers = dict(HEADERS)
    if method == 'POST':
        headers['Prefer'] = prefer
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode('utf-8')
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        raise SystemExit(f'Supabase error {exc.code}: {body}')


def list_posts(limit):
    filters = []
    if PLAYER_SLUG:
        filters.append('player_slug=eq.' + urllib.parse.quote(PLAYER_SLUG))
    filters.append('status=eq.posted')
    filters.append('select=id,player_slug,platform,platform_post_id,title,created_at')
    filters.append('order=created_at.desc')
    filters.append('limit=' + str(limit))
    posts = request_json('posts', params='&'.join(filters))
    if not posts:
        print('No posted rows found.')
        return []
    for post in posts:
        print('\n' + post['id'])
        print('  player:', post.get('player_slug'))
        print('  platform:', post.get('platform'))
        print('  platform id:', post.get('platform_post_id'))
        print('  title:', post.get('title'))
    return posts


def insert_placeholder(post_id):
    payload = {
        'post_id': post_id,
        'views': 0,
        'likes': 0,
        'comments': 0,
        'shares': 0,
        'saves': 0,
    }
    rows = request_json('post_metrics', method='POST', payload=payload)
    print('Inserted placeholder metrics for', post_id)
    return rows


def main():
    require_env()
    parser = argparse.ArgumentParser(description='Metrics scaffolding for posted soccer clips.')
    sub = parser.add_subparsers(dest='command', required=True)

    p_list = sub.add_parser('list-posts')
    p_list.add_argument('--limit', type=int, default=25)

    p_placeholder = sub.add_parser('placeholder')
    p_placeholder.add_argument('post_id')

    args = parser.parse_args()
    if args.command == 'list-posts':
        list_posts(args.limit)
    elif args.command == 'placeholder':
        insert_placeholder(args.post_id)


if __name__ == '__main__':
    main()
