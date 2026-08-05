"""End-to-end: seed Redmine -> run roadmap + issues migration -> assert the
resulting GitLab state.

Runs the whole flow TWICE, once per id-preservation strategy:

  * "keepid": `migrate-rg issues --keep-id`  -> iids set directly at create time
  * "iid":    default migration (titles carry the `-RM-<id>-MR-` marker),
              followed by the `iid` subcommand's SQL rewrite in-container

Both must converge on the same invariant: GitLab issue iid == original Redmine
issue id.
"""
import json

import pytest

from helpers import (
    GITLAB_URL, GitlabAPI, REDMINE_PROJECT_URL, E2E_DIR, run_iid_sql,
    run_migrator,
)

pytestmark = pytest.mark.e2e

MODES = {
    # mode -> (target project path, extra args for `issues`, needs SQL step)
    "keepid": ("root/target-keepid", ["--keep-id"], False),
    "iid": ("root/target-iid", [], True),
}


def _summary():
    return json.loads((E2E_DIR / "seed" / "out" / "summary.json").read_text())


@pytest.fixture(scope="session", params=list(MODES), ids=list(MODES))
def migrated(request, redmine_key, gitlab_token):
    """Run roadmap + issues for one mode; yield (api, project_path, summary)."""
    mode = request.param
    project_path, extra, needs_sql = MODES[mode]
    gitlab_url = f"{GITLAB_URL}/{project_path}"
    api = GitlabAPI(gitlab_token)

    # roadmap FIRST so issues can resolve fixed_version -> milestone_id.
    r = run_migrator("roadmap", REDMINE_PROJECT_URL, gitlab_url,
                     redmine_key, gitlab_token)
    assert r.returncode == 0, f"roadmap failed:\n{r.stdout}\n{r.stderr}"

    r = run_migrator("issues", REDMINE_PROJECT_URL, gitlab_url,
                     redmine_key, gitlab_token,
                     extra=["--custom-fields", "Customer",
                            "--closed-states", "closed,rejected", *extra])
    assert r.returncode == 0, f"issues failed:\n{r.stdout}\n{r.stderr}"

    if needs_sql:
        run_iid_sql(api.project_id(project_path))

    return api, project_path, _summary()


def _by_iid(api, project_path):
    return {i["iid"]: i for i in api.issues(project_path)}


def test_all_issues_migrated(migrated):
    api, project_path, summary = migrated
    assert len(api.issues(project_path)) == len(summary["issues"])  # 3


def test_iids_preserved(migrated):
    """Both modes must end with gitlab iid == redmine id."""
    api, project_path, summary = migrated
    got = set(_by_iid(api, project_path))
    expected = set(summary["issues"].values())
    assert got == expected


def test_no_migration_marker_left_in_titles(migrated):
    """The `-RM-<id>-MR-` marker must not survive in either mode.

    This is what distinguishes the two id strategies mechanically:
      * keepid: titles are the bare Redmine subject from the start
      * iid:    titles are created WITH the marker, then the iid SQL rewrite
                strips it -- so this passing proves the SQL rewrite actually ran
                (independent of whether iids happen to line up).
    """
    api, project_path, summary = migrated
    titles = [i["title"] for i in api.issues(project_path)]
    assert all("-RM-" not in t for t in titles), titles
    assert "Support SSL" in titles  # the real subject survived


def test_milestones_created(migrated):
    api, project_path, _ = migrated
    titles = {m["title"] for m in api.milestones(project_path)}
    assert {"v1.0", "v0.9"} <= titles


def test_rich_issue_metadata(migrated):
    api, project_path, summary = migrated
    a = _by_iid(api, project_path)[summary["issues"]["A"]]

    # labels carry tracker / category / status / priority
    labels = set(a["labels"])
    assert "Feature" in labels
    assert "Backend" in labels
    assert a["assignee"]["username"] == "bob"
    assert a["milestone"]["title"] == "v1.0"
    assert a["due_date"] is not None

    desc = a["description"]
    assert "issue id {}".format(summary["issues"]["A"]) in desc
    assert "Customer: ACME Corp" in desc          # custom field
    assert "Relations" in desc                    # relates #C
    assert "Uploads" in desc and "sample.txt" in desc  # attachment


def test_notes_migrated_and_empty_dropped(migrated):
    api, project_path, summary = migrated
    notes = api.issue_notes(project_path, summary["issues"]["A"])
    bodies = [n["body"] for n in notes]
    # alice's + charlie's notes survive; the status-only empty note is dropped.
    assert any("Started looking into this" in b for b in bodies)
    assert any("context on this too" in b for b in bodies)
    migrated_notes = [b for b in bodies if "from redmine" in b]
    assert len(migrated_notes) == 2


def test_closed_issue_state(migrated):
    api, project_path, summary = migrated
    b = _by_iid(api, project_path)[summary["issues"]["B"]]
    assert b["state"] == "closed"


def test_unmapped_author_falls_back_to_migrator(migrated):
    """Issue B is authored by 'charlie' (no GitLab user) -> attributed to root."""
    api, project_path, summary = migrated
    b = _by_iid(api, project_path)[summary["issues"]["B"]]
    assert b["author"]["username"] == "root"


# Defined LAST on purpose: it creates (and deletes) a probe issue, so it must
# run after the issue-count / iid assertions above.
def test_issue63_new_issue_iid_after_migration(migrated):
    """#63 — after migration, a brand-new issue must get a fresh iid above the
    migrated ones, not reuse a low one that will later collide.

    https://github.com/redmine-gitlab-migrator/redmine-gitlab-migrator/issues/63

    The `iid` (SQL rewrite) path now also advances GitLab's internal_ids
    counter, so both id strategies must satisfy this.
    """
    api, project_path, summary = migrated
    migrated_max = max(summary["issues"].values())

    probe = api.create_issue(project_path, "post-migration probe")
    try:
        assert probe["iid"] > migrated_max, (
            "new issue iid {} should exceed migrated max {}".format(
                probe["iid"], migrated_max))
    finally:
        api.delete_issue(project_path, probe["iid"])
