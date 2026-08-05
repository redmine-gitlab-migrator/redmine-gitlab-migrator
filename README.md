Redmine to Gitlab migrator
==========================

[![CI](https://github.com/redmine-gitlab-migrator/redmine-gitlab-migrator/actions/workflows/ci.yml/badge.svg)](https://github.com/redmine-gitlab-migrator/redmine-gitlab-migrator/actions/workflows/ci.yml)

Migrate code projects from Redmine to Gitlab, keeping issues/milestones/metadata.

It is a command-line tool (`migrate-rg`) that talks to the Redmine and GitLab
REST APIs. Migration is done per-project and in a defined order; see
[Migration process](#migration-process) below.

Does
----

- Per-project migrations
- Migration of issues, keeping as much metadata as possible:
  - redmine trackers become tags
  - redmine categories become tags
  - issues comments are kept and assigned to the right users
  - issues final status (open/closed) are kept along with open/close date (not detailed status history)
  - issues assignments are kept
  - issues numbers (ex: `#123`)
  - issues/notes authors
  - issues/notes original dates, but as comments
  - issue attachments
  - issue related changesets
  - issues custom fields (if specified)
  - relations including children and parent (although gitlab model for relations is simpler)
  - keep creation/edit dates as metadata
  - remember who closed the issue
  - convert Redmine's textile format issues to GitLab's markdown
  - possible to map to different users in GitLab
- Migration of Versions/Roadmaps keeping:
  - issues composing the version
  - statuses & due dates
- Migration of wiki pages including history:
  - versions become older commits
  - author names (without email addresses!) are the author/committer names

Does not
--------

- Migrate users, groups, and permissions (redmine ACL model is complex and
  cannot be transposed 1-1 to gitlab ACL)
- Migrate repositories (piece of cake to do by hand, + redmine allows multiple
  repositories per project where gitlab does not)
- Migrate the whole redmine installation at once, because namespacing is different in
  redmine and gitlab
- Archive the redmine project for you
- Keep "watchers" on tickets (the gitlab API does not expose them)
- Keep dates/times as metadata
- Keep track of issue relations orientation (no such notion on gitlab)
- Migrate tags ([redmine_tags](https://www.redmine.org/plugins/redmine_tags)
  plugin), as they are not exposed in gitlab API

Requires
--------

- An **API token on Redmine** (administrator) and an **API token on GitLab**
  (administrator, unless you use `--no-sudo`)
- **pandoc** (for the Textile → Markdown conversion)
- A GitLab project with **no pre-existing issues**
- The relevant users **already created in GitLab** (see [Create users](#create-users))

### Compatibility matrix

Minimum supported versions, and the versions exercised by CI on every run:

| Component | Minimum         | Tested in CI                         |
| --------- | --------------- | ------------------------------------ |
| Python    | 3.10            | 3.10, 3.11, 3.12, 3.13, 3.14         |
| Redmine   | 3.x (REST API)  | 6.1, 7.0                             |
| GitLab    | API v4 (9.0+)   | 18.11, 19.1                          |
| pandoc    | 1.17            | 3.10.1                               |

The unit tests run on every supported Python version; the end-to-end suite runs
the full Python × Redmine × GitLab matrix (see [Testing](#testing)). Older
Redmine/GitLab releases very likely still work — the migrator only relies on
long-stable API surface — but the versions above are what we actively verify.

Historically this tool was also developed/tested against much older stacks
(redmine 2.5.2 / gitlab 8.2 / python 3.4, later redmine 3.2 / gitlab 12.3 /
python 3.6).


Let's go
--------

You can or can not use
[virtualenvs](http://docs.python-guide.org/en/latest/dev/virtualenvs/), that's
up to you.

Install it:

    pip install redmine-gitlab-migrator

or latest version from GitHub:

    pip install git+https://github.com/redmine-gitlab-migrator/redmine-gitlab-migrator

or if you cloned the git (editable install):

    pip install -e .

You can then give it a check without touching anything:

    migrate-rg issues --redmine-key xxxx --gitlab-key xxxx \
      <redmine project url> <gitlab project url> --check

The `--check` here prevents any writing , it's available on all
commands.

    migrate-rg --help

Migration process
-----------------

This process is for each project, **order matters**.

### Create the gitlab project

It doesn't need to be named the same, you just have to record its URL (eg:
*https://git.example.com/mygroup/myproject*).

If your GitLab is **not served at the root of its host** but under a sub-path
(eg. *https://example.com/gitlab/mygroup/myproject*), also pass the instance
base URL so the project path can't be confused with a nested namespace:

    --gitlab-url https://example.com/gitlab

### Create users

Manual operation, project members in gitlab need to have the same username as
members in redmine. If you can't use same username in gitlab, e.g. migrating to
gitlab.com, when migrating issues you can create a mappings file with yaml format,
mapping redmine login to gitlab login, with

    --user-dict <user dict file>

Every member that interacted with the redmine project should be added to the
gitlab project. If a corresponding user can't be found in gitlab, the issue/comment
will be assigned to the gitlab admin user.

```yaml
redmine_user0: gitlab_user0
redmine_user1: gitlab_user1
```

For example, say that you have user on Redmine with username `bar` and that same user
on GitLab has username `foo`. You can save your mapping to `users.yml` file with the
following content:

```yaml
bar: foo
```

and then run the migration with `migrate-rg --user-dict users.yml`, among other flags,
assuming you are running the migration from the same directory where you stored your
user mapping.

### Migrate Roadmap

If you do use roadmaps, redmine *versions* will be converted to gitlab
*milestones*. If you don't, just skip this step.

    migrate-rg roadmap --redmine-key xxxx --gitlab-key xxxx \
      https://redmine.example.com/projects/myproject \
      http://git.example.com/mygroup/myproject --check

*(remove `--check` to perform it for real, same applies for other commands)*

### Migrate issues

    migrate-rg issues --redmine-key xxxx --gitlab-key xxxx \
      https://redmine.example.com/projects/myproject \
      http://git.example.com/mygroup/myproject --check

Note that your issue titles will be annotated with the original redmine issue
ID, like *-RM-1186-MR-logging*. This annotation will be used (and removed) by
the next step.

If you don't have direct access to the gitlab machine, e.g. migrating to gitlab.com,
and you want to keep redmine id, use --keep-id, it will create and delete issues in
gitlab for each id gap in redmine project, and won't create issues with different title.
If you have many issues in your redmine projects, it will be a slow process.

    --keep-id

At least redmine 2.1.2 has no closed_on field, so you have to specify the names of the states which define closed issues.
defaults to closed,rejected

    --closed-states closed,rejected,wontfix

If you want to migrate redmine custom fields (as description), you can specify

    --custom-fields Customer,ZendeskIssueId

If you're using SSL with self signed certificates and get an *requests.exceptions.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed (_ssl.c:600)* error, you can disable certificate validation with

    --no-verify

Migrate issues get all users in gitlab. If you have many users in your gitlab, e.g. migrating
to gitlab.com, it will be a slow process. You can use --project-members-only to query
project members instead of all users, if corresponding user can't be found in project
members, the issue/comment will be assigned to the gitlab admin user.

    --project-members-only

If you don't have admin access to gitlab instance, e.g. migrating to gitlab.com, sudo_user is not
allowed, so you have to disable sudo with

    --no-sudo

If Markdown is used in Redmine, textile conversion can be skipped with

    --no-textile

### Migrate Issues ID (iid)

You can retain the issues ID from redmine, **this cannot be done via REST
API**, thus it requires **direct access to the gitlab machine**.

So you have to log in the gitlab machine (eg. via SSH), and then issue the
command with sufficient rights, from there:

    migrate-rg iid --gitlab-key xxxx \
      http://git.example.com/mygroup/myproject --check

### Migrate wiki pages

First, clone the GitLab wiki repository (go to your project's Wiki on GitLab,
click on "Git Access" and copy the URL) somewhere local to your machine. The
conversion process works even if there are pre-existing wiki pages, however
this is NOT recommended.

    migrate-rg pages --redmine-key xxxx --gitlab-wiki xxxx \
      https://redmine.example.com/projects/myproject \

where gitlab-wiki should be the path to the cloned repository (must be local
to your machine). Add "--no-history" if you do not want the old versions of
each page to be converted, too.

After conversion, verify that everything is correct (a copy of the original
wiki page is included in the repo, however not added/committed), and then
simply push it back to GitLab.

### Import git repository

A bare matter of `git remote set-url && git push`, see git documentation.

Note that gitlab does not support multiple repositories per project, you'll have
to reorganize your projects if you were using that feature of Redmine.

### Delete all issues from gitlab

Primarily for redos in case something wasn't configured as intended

    migrate-rg delete-issues --debug --gitlab-key xxx https://git.example.com/mygroup/myproject

### Archive redmine project

If you want to.

You're good to go :).

### Optional: Redirect redmine to gitlab (for apache)

Since redmine has a common *https://redmine.company.tld/issues/{issueid}* url for issues, you can't create a generic redirect in apache.

This command creates redirect rules that you can place in your `.htaccess` file.

    migrate-rg redirect --redmine-key xxxx --gitlab-key xxxx \
      https://redmine.example.com/projects/myproject \
      http://git.example.com/mygroup/myproject > htaccess.example

The content of htaccess.example will be

    # uncomment next line to enable RewriteEngine
    # RewriteEngine On
    # Redirects from https://redmine.example.com/projects/myproject to https://git.example.com/mygroup/myproject
    RedirectMatch 301 ^/issues/1$ https://git.example.com/mygroup/myproject/issues/1
    RedirectMatch 301 ^/issues/2$ https://git.example.com/mygroup/myproject/issues/2
    ...
    RedirectMatch 301 ^/issues/999$ https://git.example.com/mygroup/myproject/999

Testing
-------

There are two test suites.

**Unit tests** — fast, no external services. They cover the conversion logic:

    pip install -e . pytest
    pytest

**End-to-end tests** — spin up real Redmine and GitLab containers, seed Redmine
with representative data, run the migration, and assert the resulting GitLab
state over its API. They are gated behind the `e2e` pytest marker (so the
command above never triggers them) and documented in [`e2e/README.md`](e2e/README.md):

    pip install -e . -r e2e/requirements-e2e.txt
    ./e2e/run.sh

Both are wired into GitHub Actions (`.github/workflows/ci.yml`): unit tests run
on every push/PR across all supported Python versions, and the end-to-end suite
runs the full Python × Redmine × GitLab matrix on a schedule / manual dispatch.

Using the Docker image
----------------------

Pull the pre-built, multi-arch (amd64/arm64) image from the GitHub Container
Registry — published by `.github/workflows/build-docker.yml`:

    docker pull ghcr.io/redmine-gitlab-migrator/redmine-gitlab-migrator:latest

or build it yourself:

    docker build -t ghcr.io/redmine-gitlab-migrator/redmine-gitlab-migrator .

The image's entrypoint is `migrate-rg`; append any subcommand to `docker run`
(with no arguments it prints `--help`):

    docker run --rm ghcr.io/redmine-gitlab-migrator/redmine-gitlab-migrator \
      roadmap --redmine-key xxxx --gitlab-key xxxx \
      https://redmine.example.com/projects/myproject \
      https://git.example.com/mygroup/myproject

    docker run --rm ghcr.io/redmine-gitlab-migrator/redmine-gitlab-migrator \
      issues --redmine-key xxxx --gitlab-key xxxx \
      https://redmine.example.com/projects/myproject \
      https://git.example.com/mygroup/myproject

Notes:

- The `pages` (wiki) command needs a local clone of the GitLab wiki repo — mount
  it, e.g. `-v "$PWD/wiki:/wiki" ... pages ... --gitlab-wiki /wiki`.
- The `iid` command talks to the GitLab database directly, so it must be run on
  the GitLab server itself, not from this image.
