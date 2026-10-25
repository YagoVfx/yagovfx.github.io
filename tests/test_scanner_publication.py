import subprocess

import pytest

from scripts.publish_scanner import DATA_FILES, publish


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


@pytest.fixture
def repositories(tmp_path):
    remote = tmp_path / 'remote.git'
    subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True)
    local = tmp_path / 'runner'
    subprocess.run(['git', 'clone', str(remote), str(local)], check=True, capture_output=True)
    git(local, 'config', 'user.name', 'Fixture')
    git(local, 'config', 'user.email', 'fixture@example.test')
    git(local, 'config', 'core.autocrlf', 'false')
    git(local, 'checkout', '-b', 'main')
    for name in DATA_FILES:
        path = local / name
        path.parent.mkdir(exist_ok=True)
        path.write_text('{}\n', encoding='utf-8')
    (local / 'scanner-version.txt').write_text('old', encoding='utf-8')
    git(local, 'add', '.')
    git(local, 'commit', '-m', 'initial')
    git(local, 'push', '-u', 'origin', 'main')
    other = tmp_path / 'desktop'
    subprocess.run(['git', 'clone', '--branch', 'main', str(remote), str(other)], check=True, capture_output=True)
    git(other, 'config', 'user.name', 'User')
    git(other, 'config', 'user.email', 'user@example.test')
    return local, other, remote


def test_rejected_push_regenerates_using_new_code_and_preserves_user_changes(repositories):
    local, other, remote = repositories
    (local / 'uncommitted.txt').write_text('keep this local file', encoding='utf-8')
    calls = []

    def generate(worktree):
        version = (worktree / 'scanner-version.txt').read_text(encoding='utf-8')
        calls.append(version)
        (worktree / 'data/jobs.json').write_text('{"version":"' + version + '"}\n', encoding='utf-8')
        if len(calls) == 1:
            (other / 'scanner-version.txt').write_text('new', encoding='utf-8')
            (other / 'user-feature.txt').write_text('preserve', encoding='utf-8')
            git(other, 'add', '.')
            git(other, 'commit', '-m', 'user feature')
            git(other, 'push', 'origin', 'main')

    assert publish(local, generator=generate) is True
    assert calls == ['old', 'new']
    assert git(remote, 'show', 'main:scanner-version.txt') == 'new'
    assert git(remote, 'show', 'main:user-feature.txt') == 'preserve'
    assert git(remote, 'show', 'main:data/jobs.json') == '{"version":"new"}'
    assert (local / 'uncommitted.txt').read_text() == 'keep this local file'
    assert git(local, 'worktree', 'list', '--porcelain').count('worktree ') == 1


def test_no_changes_does_not_create_a_commit(repositories):
    local, _, remote = repositories
    before = git(remote, 'rev-parse', 'main')
    assert publish(local, generator=lambda worktree: None) is False
    assert git(remote, 'rev-parse', 'main') == before


def test_failed_scan_never_publishes_partial_data(repositories):
    local, _, remote = repositories
    before = git(remote, 'rev-parse', 'main')

    def fail(worktree):
        (worktree / 'data/jobs.json').write_text('partial', encoding='utf-8')
        raise RuntimeError('scanner failed')

    with pytest.raises(RuntimeError, match='scanner failed'):
        publish(local, generator=fail)
    assert git(remote, 'rev-parse', 'main') == before
    assert git(local, 'worktree', 'list', '--porcelain').count('worktree ') == 1


def test_continuous_updates_stop_after_three_attempts_without_overwriting(repositories):
    local, other, remote = repositories
    calls = []

    def race(worktree):
        calls.append(len(calls) + 1)
        (worktree / 'data/jobs.json').write_text('generated', encoding='utf-8')
        (other / 'scanner-version.txt').write_text(str(len(calls)), encoding='utf-8')
        git(other, 'add', '.')
        git(other, 'commit', '-m', 'concurrent user update')
        git(other, 'push', 'origin', 'main')

    with pytest.raises(RuntimeError, match='Main kept changing'):
        publish(local, generator=race)
    assert len(calls) == 3
    assert git(remote, 'show', 'main:data/jobs.json') == '{}'
    assert git(remote, 'show', 'main:scanner-version.txt') == '3'
