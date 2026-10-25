"""Publish generated feeds from an isolated checkout of the latest main.

Never rebase or force-push generated JSON. If main advances during a scan,
discard that temporary scan and generate again using the new code and data.
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile


DATA_FILES = (
    'data/jobs.json', 'data/scanner-status.json', 'data/scanner-report.json',
    'data/companies-registry.json', 'data/company-locations.json',
    'data/mobile-careers.json', 'data/public-exams.json',
)


def git(repo, *args, check=True):
    return subprocess.run(['git', '-C', str(repo), *args], check=check,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def latest(repo, branch):
    git(repo, 'fetch', '--no-tags', 'origin', 'refs/heads/' + branch)
    return git(repo, 'rev-parse', 'FETCH_HEAD').stdout.strip()


def generate(worktree):
    commands = [
        [sys.executable, '-m', 'pip', 'install', '-r', 'scanner/requirements.txt', 'pytest'],
        [sys.executable, '-m', 'pytest', '-q', 'tests', '--ignore=tests/e2e'],
        [sys.executable, 'scanner/scanner.py'],
        [sys.executable, '-m', 'scanner.build_registry'],
        [sys.executable, '-m', 'scanner.map_locations'],
        [sys.executable, '-m', 'scanner.mobile_careers'],
        [sys.executable, '-m', 'scanner.public_exams'],
    ]
    for command in commands:
        subprocess.run(command, cwd=worktree, check=True)


def publish(repo, branch='main', attempts=3, generator=generate):
    repo = Path(repo).resolve()
    base = latest(repo, branch)
    for attempt in range(1, attempts + 1):
        print(f'Scanner publication {attempt}/{attempts}, base {base[:12]}', flush=True)
        # Only this newly allocated, checked path may be removed by worktree cleanup.
        with tempfile.TemporaryDirectory(prefix='yago-scanner-publish-') as temporary:
            parent = Path(temporary).resolve()
            worktree = parent / 'checkout'
            git(repo, 'worktree', 'add', '--detach', str(worktree), base)
            try:
                generator(worktree)
                git(worktree, 'add', '--', *DATA_FILES)
                diff = git(worktree, 'diff', '--cached', '--quiet', check=False)
                if diff.returncode == 0:
                    print('No generated data changes.', flush=True)
                    return False
                if diff.returncode != 1:
                    raise RuntimeError(diff.stderr or 'Cannot inspect generated data changes')
                git(worktree, '-c', 'user.name=github-actions[bot]',
                    '-c', 'user.email=github-actions[bot]@users.noreply.github.com',
                    'commit', '-m', 'chore: update VFX jobs [automated]')
                push = git(worktree, 'push', 'origin', 'HEAD:refs/heads/' + branch, check=False)
                if push.returncode == 0:
                    print(push.stdout + push.stderr, flush=True)
                    return True
                print(push.stdout + push.stderr, flush=True)
                updated = latest(repo, branch)
                if updated == base:
                    raise RuntimeError('Push failed without a concurrent update: ' + push.stderr)
                if attempt == attempts:
                    raise RuntimeError('Main kept changing during publication; retry the workflow. No remote changes were overwritten.')
                print('Main advanced. Re-running tests and scanner on the new revision.', flush=True)
                base = updated
            finally:
                if worktree.resolve().parent != parent or worktree.name != 'checkout':
                    raise RuntimeError('Unexpected temporary worktree cleanup path')
                git(repo, 'worktree', 'remove', '--force', str(worktree))
    raise RuntimeError('No publication attempts configured')


if __name__ == '__main__':
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('This publisher is reserved for GitHub Actions; use GitHub Desktop locally.')
    publish(Path(__file__).resolve().parents[1])
