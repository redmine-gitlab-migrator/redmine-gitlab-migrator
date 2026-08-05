"""Thin helpers for driving the e2e stack: running the migrator, poking the
GitLab API to assert final state, and running the iid SQL in-container.
"""
import json
import subprocess
import time
from pathlib import Path

import requests

E2E_DIR = Path(__file__).resolve().parent
COMPOSE_FILE = E2E_DIR / "docker-compose.e2e.yml"

REDMINE_URL = "http://localhost:3000"
GITLAB_URL = "http://localhost:8929"

# The migrator addresses projects by these URLs.
REDMINE_PROJECT_URL = f"{REDMINE_URL}/projects/testproj"


def compose(*args, check=True, capture=False, input_=None):
    """Run a `docker compose` subcommand against the e2e stack."""
    cmd = ["docker", "compose", "-f", str(COMPOSE_FILE), *args]
    return subprocess.run(
        cmd, check=check, text=True, input=input_,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def read_seed_out(name):
    """Read a file the seed scripts dropped in e2e/seed/out/."""
    return (E2E_DIR / "seed" / "out" / name).read_text().strip()


# --------------------------------------------------------------------------
# Running the migrator (host-side; must be pip install -e .'d)
# --------------------------------------------------------------------------
# Which positional args / keys each subcommand's argparse parser actually
# accepts (mirrors commands.py:parse_args). Passing an unaccepted flag makes
# argparse bail with "unrecognized arguments".
_TAKES_REDMINE_URL = {"issues", "pages", "roadmap", "redirect"}
_TAKES_GITLAB_URL = {"issues", "roadmap", "redirect", "iid", "delete-issues"}
_TAKES_REDMINE_KEY = {"issues", "pages", "roadmap", "redirect"}
_TAKES_GITLAB_KEY = {"issues", "roadmap", "redirect", "iid", "delete-issues"}


def run_migrator(subcommand, redmine_url, gitlab_url, redmine_key, gitlab_key,
                 extra=(), bin_="migrate-rg"):
    cmd = [bin_, subcommand]
    if subcommand in _TAKES_REDMINE_URL:
        cmd += [redmine_url]
    if subcommand in _TAKES_GITLAB_URL:
        cmd += [gitlab_url]
    if subcommand in _TAKES_REDMINE_KEY:
        cmd += ["--redmine-key", redmine_key]
    if subcommand in _TAKES_GITLAB_KEY:
        cmd += ["--gitlab-key", gitlab_key]
    cmd += list(extra)
    return subprocess.run(cmd, text=True, capture_output=True)


# --------------------------------------------------------------------------
# GitLab REST assertions
# --------------------------------------------------------------------------
class GitlabAPI:
    def __init__(self, token, base=GITLAB_URL):
        self.base = f"{base}/api/v4"
        self.h = {"PRIVATE-TOKEN": token}

    def _get(self, path, **params):
        params.setdefault("per_page", 100)
        r = requests.get(f"{self.base}{path}", headers=self.h, params=params)
        r.raise_for_status()
        return r.json()

    def project_id(self, full_path):
        return self._get(f"/projects/{requests.utils.quote(full_path, safe='')}")["id"]

    def issues(self, full_path):
        pid = self.project_id(full_path)
        return self._get(f"/projects/{pid}/issues", scope="all", state="all")

    def issue_notes(self, full_path, iid):
        pid = self.project_id(full_path)
        return self._get(f"/projects/{pid}/issues/{iid}/notes")

    def create_issue(self, full_path, title):
        pid = self.project_id(full_path)
        r = requests.post(f"{self.base}/projects/{pid}/issues",
                          headers=self.h, data={"title": title})
        r.raise_for_status()
        return r.json()

    def delete_issue(self, full_path, iid):
        pid = self.project_id(full_path)
        requests.delete(f"{self.base}/projects/{pid}/issues/{iid}", headers=self.h)

    def milestones(self, full_path):
        pid = self.project_id(full_path)
        return self._get(f"/projects/{pid}/milestones", state="all")


# --------------------------------------------------------------------------
# iid recovery — the `iid` subcommand's SQL, executed where it's meant to run:
# inside the GitLab (omnibus) container. Imports the exact SQL templates from
# the package so the test stays in lock-step with the shipped command.
# --------------------------------------------------------------------------
def run_iid_sql(project_id):
    from redmine_gitlab_migrator import sql

    regex = r"-RM-([0-9]+)-MR-(.*)"
    for template in (sql.UPDATE_IID_ISSUES, sql.MIGRATE_IID_ISSUES,
                     sql.UPDATE_INTERNAL_ID_ISSUES):
        # UPDATE_INTERNAL_ID_ISSUES has no {regex} placeholder; str.format
        # ignores the extra kwarg.
        stmt = template.format(regex=regex, project_id=project_id)
        compose("exec", "-T", "gitlab", "gitlab-psql", "-d",
                "gitlabhq_production", "-c", stmt, capture=True)


def wait_for_http(url, timeout=600, interval=5):
    """Block until an HTTP endpoint answers (any status), or raise."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            requests.get(url, timeout=5)
            return
        except requests.exceptions.RequestException:
            time.sleep(interval)
    raise TimeoutError(f"{url} not reachable within {timeout}s")
