#!/usr/bin/env python3
import ast
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    'scripts/post.py',
    'scripts/queue.py',
    'scripts/summary.py',
    'scripts/cleanup.py',
    'scripts/metrics.py',
    'scripts/validate_project.py',
    'supabase/migrations/001_content_queue.sql',
    'supabase/migrations/002_duplicate_detection_and_size.sql',
    '.github/workflows/post-cherki.yml',
    '.github/workflows/post-bellingham.yml',
    '.github/workflows/post-yamal.yml',
    '.github/workflows/manual-worker.yml',
    '.github/workflows/validate.yml',
    '.github/workflows/build-dashboard.yml',
    '.env.example',
    'README.md',
    'DEPLOYMENT.md',
    'LOCAL_TESTING.md',
    'package.json',
    'pages/index.js',
    'pages/login.js',
    'pages/api/login.js',
    'pages/api/logout.js',
    'pages/api/health.js',
    'pages/api/candidates/[id].js',
    'lib/supabaseRest.js',
    'lib/dashboardAuth.js',
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
    'normalized_title',
    'video_size_bytes',
    "'cherki'",
    "'bellingham'",
    "'yamal'",
]

POST_REQUIRED_TERMS = [
    'MODE=discover',
    'MODE=process',
    'MODE=post',
    'MODE=auto',
    'MAX_VIDEO_BYTES',
    'normalized_title',
    'def discover',
    'def process_next',
    'def post_next',
    'def load_player_defaults',
    'def validate_video_size',
]

DASHBOARD_REQUIRED_TERMS = {
    'pages/index.js': ['requestIsAuthed', 'supabaseGet', 'CandidateCard', 'DashboardStats', 'formatBytes', 'formatAge', 'ACTIONS_URL', '/api/candidates/', '/api/logout', '/api/health'],
    'pages/login.js': ['action="/api/login"', 'Dashboard login'],
    'pages/api/login.js': ['makeAuthCookie', 'passwordMatches', 'req.body.password'],
    'pages/api/logout.js': ['dashboard_auth=', 'Max-Age=0'],
    'pages/api/health.js': ['requestIsAuthed', 'players', 'clip_candidates', 'posts'],
    'pages/api/candidates/[id].js': ['requestIsAuthed', 'supabasePatch', 'ALLOWED_STATUSES'],
    'lib/dashboardAuth.js': ['DASHBOARD_PASSWORD', 'NODE_ENV', 'HttpOnly', 'SameSite=Lax'],
    'lib/supabaseRest.js': ['SUPABASE_SERVICE_KEY', 'supabaseGet', 'supabasePatch'],
}

SCRIPT_REQUIRED_TERMS = {
    'scripts/cleanup.py': ['list-failed', 'list-rejected', 'reset-failed'],
    'scripts/metrics.py': ['list-posts', 'placeholder', 'post_metrics'],
}

MANUAL_WORKFLOW_TERMS = [
    'workflow_dispatch:',
    'player_slug:',
    'mode:',
    'discover',
    'process',
    'post',
    'auto',
    'POST_TO_IG: \'false\'',
    'POST_TO_TIKTOK: \'false\'',
]

BUILD_WORKFLOW_TERMS = [
    'npm install',
    'npm run build',
    'DASHBOARD_PASSWORD',
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
    for path in ['scripts/post.py', 'scripts/queue.py', 'scripts/summary.py', 'scripts/cleanup.py', 'scripts/metrics.py', 'scripts/validate_project.py']:
        try:
            ast.parse(read(path), filename=path)
        except SyntaxError as exc:
            fail(f'python syntax error in {path}: {exc}')


def check_package_json():
    try:
        data = json.loads(read('package.json'))
    except json.JSONDecodeError as exc:
        fail(f'package.json is invalid JSON: {exc}')
    for dependency in ['next', 'react', 'react-dom']:
        if dependency not in data.get('dependencies', {}):
            fail(f'package.json missing dependency {dependency}')


def check_workflows():
    for path, expected_slug_line in WORKFLOWS.items():
        content = read(path)
        for required in ['on:', 'workflow_dispatch:', 'schedule:', 'runs-on: ubuntu-latest', 'python scripts/post.py']:
            if required not in content:
                fail(f'{path} missing {required}')
        if expected_slug_line not in content:
            fail(f'{path} has wrong or missing slug line')
    manual = read('.github/workflows/manual-worker.yml')
    for term in MANUAL_WORKFLOW_TERMS:
        if term not in manual:
            fail(f'manual worker workflow missing {term}')
    dashboard_build = read('.github/workflows/build-dashboard.yml')
    for term in BUILD_WORKFLOW_TERMS:
        if term not in dashboard_build:
            fail(f'build-dashboard workflow missing {term}')


def check_sql():
    combined = (read('supabase/migrations/001_content_queue.sql') + read('supabase/migrations/002_duplicate_detection_and_size.sql')).lower()
    for term in SQL_REQUIRED_TERMS:
        if term.lower() not in combined:
            fail(f'migration missing {term}')


def check_worker_contract():
    content = read('scripts/post.py')
    for term in POST_REQUIRED_TERMS:
        if term not in content:
            fail(f'post.py missing {term}')
    if 'discover(tmpdir)\n            process_next(tmpdir)\n            post_next()' not in content:
        fail('MODE=auto does not run discover, process, and post in order')


def check_dashboard_contract():
    for path, terms in DASHBOARD_REQUIRED_TERMS.items():
        content = read(path)
        for term in terms:
            if term not in content:
                fail(f'{path} missing {term}')


def check_script_contracts():
    for path, terms in SCRIPT_REQUIRED_TERMS.items():
        content = read(path)
        for term in terms:
            if term not in content:
                fail(f'{path} missing {term}')


def main():
    check_files_exist()
    check_python_syntax()
    check_package_json()
    check_workflows()
    check_sql()
    check_worker_contract()
    check_dashboard_contract()
    check_script_contracts()
    print('Project validation passed.')


if __name__ == '__main__':
    main()
