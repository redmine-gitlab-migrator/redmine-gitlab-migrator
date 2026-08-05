# End-to-end tests

These tests exercise the migrator against **real** Redmine and GitLab instances
running in Docker: seed Redmine with a representative dataset, run the migration,
then assert the resulting GitLab state over its REST API.

They are **slow** (GitLab CE takes 3–6 minutes just to boot) and gated behind the
`e2e` pytest marker, so they never run as part of the normal unit-test suite.

## What's covered

- `roadmap` → GitLab milestones (open + closed versions)
- `issues` → issues with labels (tracker/category/status/priority), assignee,
  milestone, due date, custom field, relations, attachment upload, notes
  (empty status-only notes dropped), closed state, and the unmapped-author
  fallback to the migrator account
- **Two id-preservation modes**, run as a parametrized suite:
  - `keepid` — `migrate-rg issues --keep-id`
  - `iid` — default migration + the `iid` subcommand's SQL rewrite, executed
    inside the GitLab container (where that command is designed to run)
- `pages` → wiki pages (with history) committed to the GitLab wiki repo

## Requirements

- Docker + Docker Compose v2, with ~6 GB RAM available to Docker (GitLab is hungry)
- On Apple Silicon (arm64) the pinned `gitlab-ce` image runs under **amd64
  emulation**, so first boot is slow (allow 5–8 min). It works, but if you want
  it faster use a native arm64 GitLab tag where available.
- The migrator installed locally so `migrate-rg` is on PATH:

```bash
pip install -e .
pip install -r e2e/requirements-e2e.txt
```

## Running

```bash
./e2e/run.sh                 # up → seed → test → down
E2E_KEEP_STACK=1 ./e2e/run.sh   # leave containers running to iterate
```

Or manually:

```bash
docker compose -f e2e/docker-compose.e2e.yml up -d
pytest e2e -m e2e -v
docker compose -f e2e/docker-compose.e2e.yml down -v
```

Useful env vars:

- `E2E_KEEP_STACK=1` — don't tear the stack down after the session
- `E2E_REUSE_STACK=1` — assume the stack is already up (skip `compose up`)
- `REDMINE_TAG` / `GITLAB_TAG` — override the Docker image tags (the CI matrix
  uses these; defaults are set in `docker-compose.e2e.yml`)

## Version matrix & compatibility

Image tags are matrix-driven from `.github/workflows/ci.yml`; the compose file
reads `REDMINE_TAG` / `GITLAB_TAG`. The seed scripts have to account for a few
things that changed across supported versions:

- **Redmine 7.0 / Rails 8** requires the standard `SECRET_KEY_BASE` env var for
  `rails runner` (set in the compose file).
- **GitLab 19.x (Organizations/Cells)** requires `organization_id` when creating
  users; `setup_gitlab.rb` passes it when the feature is present and still works
  on 18.x without it.
- Redmine ships **no default data** in the official image (roles/trackers/etc.);
  the seed loads it via `Redmine::DefaultData::Loader`.

Because the seed touches model internals, bumping an image tag may require a
corresponding tweak to the seed scripts — that's exactly what the matrix is
there to catch.

## Layout

| File | Purpose |
| --- | --- |
| `docker-compose.e2e.yml` | Redmine (+ postgres) and GitLab CE, pinned versions |
| `seed/seed_redmine.rb` | Rails-runner script seeding the Redmine fixture data |
| `seed/setup_gitlab.rb` | Rails-runner script: users, root token, empty target projects |
| `seed/sample.txt` | Attachment fixture |
| `conftest.py` | Fixtures: bring up stack, seed, expose credentials |
| `helpers.py` | Migrator invocation + GitLab API assertions + iid SQL |
| `test_e2e_migration.py` | issues + roadmap, both id modes |
| `test_e2e_pages.py` | wiki pages |

## Real-world requirements this suite surfaced

Getting the migration to actually work end-to-end revealed constraints worth
knowing when running a real migration (encoded in `seed/setup_gitlab.rb`):

- **Mapped users must be members of the target GitLab project.** The migrator
  attributes issues/notes to their original author via the `SUDO` header. If the
  impersonated user can't see the (private) project, GitLab replies with a
  confusing `404 Project Not Found` — not a permissions error.
- **For `--keep-id`, those members must be *Owners*.** Setting a custom `iid` at
  creation time is only honoured for admins / project owners; a SUDO'd create by
  a mere Developer silently gets an auto-assigned iid, so numbering isn't
  preserved.
- The official `redmine` image ships with **no default data** — the seed loads
  roles/trackers/statuses/priorities via `Redmine::DefaultData::Loader`.
- GitLab's `initial_root_password` must pass a strength check (no dictionary
  words like "password").

## Known gaps / notes

- Seed scripts touch Redmine/GitLab **model internals**, so they're pinned to
  `redmine:5.1` and `gitlab/gitlab-ce:16.11`. Bump the images and the seed
  scripts together.
- The `--archive-account` branch isn't directly exercised: with `--sudo` and a
  present `root` user, unmapped authors already fall back to the migrator, so
  the KeyError path that `--archive-account` guards doesn't trigger. Left as a
  follow-up.
- Not yet wired into CI. Because of the GitLab boot cost this belongs in a
  manual / nightly workflow, not on every push (see MAINTENANCE.md).
