"""Pytest fixtures that bring up the e2e stack, seed both sides, and hand the
tests ready-to-use credentials.

All tests here are marked `e2e` and are NOT collected by the normal unit-test
run (see pytest.ini). Run explicitly with:

    pip install -e .
    pytest e2e -m e2e

Set E2E_KEEP_STACK=1 to leave the containers running after the session (handy
while iterating on assertions — bring-up is the expensive part).
"""
import json
import os
import re
from pathlib import Path

import pytest

from helpers import (
    E2E_DIR, GITLAB_URL, REDMINE_URL, compose, wait_for_http,
)

OUT_DIR = E2E_DIR / "seed" / "out"


def _persist_seed_outputs(redmine_stdout, gitlab_stdout):
    """Parse the machine-readable lines the seed scripts print and write them
    host-side (the /seed mount is read-only inside the containers)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    m = re.search(r"^REDMINE_API_KEY=(\S+)", redmine_stdout, re.M)
    assert m, f"seed_redmine.rb did not print REDMINE_API_KEY:\n{redmine_stdout}"
    (OUT_DIR / "redmine_key.txt").write_text(m.group(1))

    m = re.search(r"^SEED_OK (\{.*\})", redmine_stdout, re.M)
    assert m, f"seed_redmine.rb did not print SEED_OK json:\n{redmine_stdout}"
    (OUT_DIR / "summary.json").write_text(
        json.dumps(json.loads(m.group(1)), indent=2))

    m = re.search(r"GITLAB_OK token=(\S+)", gitlab_stdout)
    assert m, f"setup_gitlab.rb did not print GITLAB_OK token:\n{gitlab_stdout}"
    (OUT_DIR / "gitlab_token.txt").write_text(m.group(1))


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: full docker-based end-to-end test")


@pytest.fixture(scope="session")
def stack():
    """Bring up redmine + gitlab, wait for health, seed both, yield creds."""
    keep = os.environ.get("E2E_KEEP_STACK") == "1"
    already = os.environ.get("E2E_REUSE_STACK") == "1"

    if not already:
        # Start from a clean slate: a half-initialised GitLab volume left over
        # from a previous run can leave the DB migrated-but-unseeded (no root
        # user). `down -v` guarantees fresh anonymous volumes.
        compose("down", "-v", check=False)
        compose("up", "-d")

    # GitLab is the slow one; its healthcheck has a 300s start_period.
    print("Waiting for Redmine...")
    wait_for_http(f"{REDMINE_URL}/login", timeout=300)
    print("Waiting for GitLab (this takes several minutes)...")
    wait_for_http(f"{GITLAB_URL}/users/sign_in", timeout=600)

    print("Seeding Redmine...")
    red = compose("exec", "-T", "redmine", "bundle", "exec", "rails", "runner",
                  "/seed/seed_redmine.rb", capture=True)
    print("Setting up GitLab...")
    gl = compose("exec", "-T", "gitlab", "gitlab-rails", "runner",
                 "/seed/setup_gitlab.rb", capture=True)

    _persist_seed_outputs(red.stdout, gl.stdout)

    creds = {
        "redmine_key": (OUT_DIR / "redmine_key.txt").read_text().strip(),
        "gitlab_token": (OUT_DIR / "gitlab_token.txt").read_text().strip(),
    }
    yield creds

    if not keep:
        compose("down", "-v", check=False)


@pytest.fixture(scope="session")
def redmine_key(stack):
    return stack["redmine_key"]


@pytest.fixture(scope="session")
def gitlab_token(stack):
    return stack["gitlab_token"]
