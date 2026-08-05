"""Tests that pin down behaviour reported in GitHub bug issues.

- `xfail` tests REPRODUCE a bug that is still open: they assert the *correct*
  behaviour and are expected to fail until the bug is fixed (at which point they
  flip to xpass and the marker can be removed).
- The plain (passing) tests are REGRESSION guards for issues that the current
  code already handles, so a future change can't silently reintroduce them.
"""
import pytest

from redmine_gitlab_migrator.gitlab import GitlabProject
from redmine_gitlab_migrator.converters import convert_issue
from redmine_gitlab_migrator.wiki import NopConverter


def _make_issue(**overrides):
    """A minimal redmine-API-style issue dict for convert_issue()."""
    issue = {
        "id": 1,
        "subject": "Something",
        "description": "",
        "created_on": "2020-01-01T00:00:00Z",
        "status": {"name": "New"},
        "tracker": {"name": "Bug"},
        "priority": {"name": "Normal"},
        "author": {"id": 1, "name": "Admin"},
        "journals": [],
    }
    issue.update(overrides)
    return issue


def _convert(issue, milestones=None):
    redmine_users = {1: {"id": 1, "login": "root"}}
    gitlab_users = {"root": {"id": 1, "username": "root"}}
    return convert_issue(
        "apikey", issue, redmine_users, gitlab_users, milestones or {},
        [], [], NopConverter(), "root", keep_title=False, sudo=True,
        archive_acc=None)


# --------------------------------------------------------------------------
# #42 — GitLab installed at a sub-path of the host (not at the URL root)
# https://github.com/redmine-gitlab-migrator/redmine-gitlab-migrator/issues/42
#
# Fixed by letting the caller pass the GitLab instance base URL (`--gitlab-url`
# / `base_url=`); the URL regex alone can't tell a sub-path install from a
# nested namespace.
# --------------------------------------------------------------------------
def test_issue42_gitlab_served_under_url_subpath():
    project = GitlabProject("https://host.example.com/git/mygroup/myproject",
                            client=object(),
                            base_url="https://host.example.com/git")
    # The '/git' sub-path survives into the API and instance URLs, and the
    # namespace/project path is everything after the base.
    assert project.instance_url == "https://host.example.com/git/api/v4"
    assert project.api_url == (
        "https://host.example.com/git/api/v4/projects/mygroup%2Fmyproject")


def test_gitlab_at_host_root_still_works():
    """Regression guard: without base_url, a nested namespace resolves correctly
    and the instance URL has no '//api/v4' double slash."""
    project = GitlabProject("https://host.example.com/group/subgroup/project",
                            client=object())
    assert project.instance_url == "https://host.example.com/api/v4"
    assert project.api_url == (
        "https://host.example.com/api/v4/projects/group%2Fsubgroup%2Fproject")


# --------------------------------------------------------------------------
# #14 — Issue import must not fail when the milestone/roadmap wasn't migrated
# https://github.com/redmine-gitlab-migrator/redmine-gitlab-migrator/issues/14
# Regression guard: an issue whose fixed_version has no matching GitLab
# milestone should convert cleanly, just without a milestone_id.
# --------------------------------------------------------------------------
def test_issue14_missing_milestone_does_not_crash():
    issue = _make_issue(fixed_version={"id": 9, "name": "NeverMigrated"})
    data, meta, rid = _convert(issue, milestones={})  # empty milestone index
    assert "milestone_id" not in data


# --------------------------------------------------------------------------
# #3 — Issue assigned to a Redmine *group* (not a user)
# https://github.com/redmine-gitlab-migrator/redmine-gitlab-migrator/issues/3
# Regression guard: a group assignee (whose id isn't a known user) must not
# crash; the group name is preserved as a label instead.
# --------------------------------------------------------------------------
def test_issue3_group_assignee_becomes_label():
    issue = _make_issue(assigned_to={"id": 777, "name": "DevTeam"})
    data, meta, rid = _convert(issue)
    assert "assignee_id" not in data          # group is not a mappable user
    assert "DevTeam" in data["labels"].split(",")


# --------------------------------------------------------------------------
# #49 (PR) — Issue whose description is JSON null must not crash
# https://github.com/redmine-gitlab-migrator/redmine-gitlab-migrator/pull/49
# Redmine can return "description": null (not just "" or an absent key). The
# textile converter then crashes on None.split(). Regression guard: a null
# description converts cleanly and does not leak the literal string "None"
# into the GitLab body. Uses the real TextileConverter to exercise the crash.
# --------------------------------------------------------------------------
def test_issue49_null_description_does_not_crash():
    from redmine_gitlab_migrator.wiki import TextileConverter
    redmine_users = {1: {"id": 1, "login": "root"}}
    gitlab_users = {"root": {"id": 1, "username": "root"}}
    data, meta, rid = convert_issue(
        "apikey", _make_issue(description=None), redmine_users, gitlab_users,
        {}, [], [], TextileConverter(), "root", keep_title=False, sudo=True,
        archive_acc=None)
    assert not data["description"].lstrip().startswith("None")
