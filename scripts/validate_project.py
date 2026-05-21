#!/usr/bin/env python3
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    'scripts/post.py',
    'scripts/queue.py',
    'supabase/migrations/001_content_queue.sql',
    '.github/workflows/post-cherki.yml',
    '.github/workflows/post-bellingham.yml',
    '.github/workflows/post-yamal.yml',
    '.env.example',
    'README.md',
]

WORKFLOWS = {
    '.github/workflows/post-cherki.yml': 'PLAYER_SLUG:           cherki',
    '.github/workflows/post-bellingham.yml': 'PLAYER_SLUG:           bellingham',
    '.github/workflows/post-yamal.yml': 'PLAYER_SLUG:           yamal',
}

SQL_REQUIRED_TERMS = [
    'create table if not exists public.players',
    'create table if not exists public.clip_candidates',
    'create table if not exists public.posts',
    'create table if not exists public.post_metrics',
    "'cherki'",
    "'bellingham'",
    "'yamal'",
]

POST_REQUIRED_TERMS = [
    'MODE=discover',
    'MODE=process',
    'MODE=post',
    'MODE=auto',
    'def discover',
    'def process_next',
    'def post_next',
    'def load_player_defaults',
]


def fail(message):
    print('FAIL:', message)
    sys.exit(1)


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def check_files_exist():
    for path in REQUIRED_FILES:
        if not (ROOT / path).exists():
            fail(f'missing required file: {path}')


def check_python_syntax():
    for path in ['scripts/post.py', 'scripts/queue.py']:
        try:
            ast.parse(read(path), filename=path)
        except SyntaxError as exc:
            fail(f'python syntax error in {path}: {exc}')


def check_workflows():
    for path, expected_slug_line in WORKFLOWS.items():
        content = read(path)
        for required in ['on:', 'workflow_dispatch:', 'schedule:', 'runs-on: ubuntu-latest', 'python scripts/post.py']:
            if required not in content:
                fail(f'{path} missing {required}')
        if expected_slug_line not in content:
            fail(f'{path} has wrong or missing slug line')


def check_sql():
    content = read('supabase/migrations/001_content_queue.sql').lower()
    for term in SQL_REQUIRED_TERMS:
        if term.lower() not in content:
            fail(f'migration missing {term}')


def check_worker_contract():
    content = read('scripts/post.py')
    for term in POST_REQUIRED_TERMS:
        if term not in content:
            fail(f'post.py missing {term}')
    if 'discover(tmpdir)\n            process_next(tmpdir)\n            post_next()' not in content:
        fail('MODE=auto does not run discover, process, and post in order')


def main():
    check_files_exist()
    check_python_syntax()
    check_workflows()
    check_sql()
    check_worker_contract()
    print('Project validation passed.')


if __name__ == '__main__':
    main()
