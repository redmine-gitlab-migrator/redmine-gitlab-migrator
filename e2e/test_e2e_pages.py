"""End-to-end for the `pages` (wiki) command.

The command converts Redmine wiki pages (incl. history) into commits on a LOCAL
clone of the GitLab project's wiki git repo. It does not push — so the test:

  1. initialises the wiki repo (create one page via API),
  2. clones it,
  3. runs `migrate-rg pages --gitlab-wiki <clone>` (writes + commits .md files),
  4. pushes,
  5. asserts the pages exist via the GitLab wiki API.
"""
import subprocess

import pytest
import requests

from helpers import (
    GITLAB_URL, REDMINE_PROJECT_URL, GitlabAPI, run_migrator,
)

pytestmark = pytest.mark.e2e

PROJECT_PATH = "root/target-keepid"


@pytest.fixture
def wiki_clone(tmp_path, gitlab_token):
    api = GitlabAPI(gitlab_token)
    pid = api.project_id(PROJECT_PATH)

    # Initialise the wiki repo by creating a placeholder page via the API.
    requests.post(
        f"{GITLAB_URL}/api/v4/projects/{pid}/wikis",
        headers={"PRIVATE-TOKEN": gitlab_token},
        data={"title": "placeholder", "content": "init"},
    ).raise_for_status()

    clone_url = (f"http://root:{gitlab_token}@localhost:8929/"
                 f"{PROJECT_PATH}.wiki.git")
    dest = tmp_path / "wiki"
    subprocess.run(["git", "clone", clone_url, str(dest)], check=True,
                   capture_output=True, text=True)
    subprocess.run(["git", "-C", str(dest), "config", "user.email",
                    "e2e@example.com"], check=True)
    subprocess.run(["git", "-C", str(dest), "config", "user.name", "e2e"],
                   check=True)
    return dest, clone_url


def test_wiki_pages_migrated(wiki_clone, redmine_key, gitlab_token):
    dest, clone_url = wiki_clone

    r = run_migrator("pages", REDMINE_PROJECT_URL, "",
                     redmine_key, gitlab_token,
                     extra=["--gitlab-wiki", str(dest)])
    # `pages` doesn't take a gitlab project/key; run_migrator only appends the
    # redmine url + redmine key for this subcommand.
    assert r.returncode == 0, f"pages failed:\n{r.stdout}\n{r.stderr}"

    subprocess.run(["git", "-C", str(dest), "push"], check=True,
                   capture_output=True, text=True)

    api = GitlabAPI(gitlab_token)
    pid = api.project_id(PROJECT_PATH)
    wikis = requests.get(
        f"{GITLAB_URL}/api/v4/projects/{pid}/wikis",
        headers={"PRIVATE-TOKEN": gitlab_token},
    ).json()
    slugs = {w["slug"].lower() for w in wikis}
    # 'Wiki' start page is renamed to 'home' by the converter; 'Details' too.
    assert "home" in slugs
    assert any("details" in s for s in slugs)
