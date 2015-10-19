Redmine to gitlab migrator
==========================

Does
----

- Per-project migrations
- migration of issues, keeping as much metadata as possible
  - your trackers become tags
  - issue comments are kept and assigned to the right users
  - issues assignations are kept
  - keep issues numbers (ex: `#123`)
  - keep issue/notes authors
  - keep track of issue/notes original dates, but as comments
  - keeps relations (although gitlab model for relations is simpler)


Does not
--------

- Migrate users and groups, and permissions (redmine ACL model is complex and
  cannot be transposed 1-1 to gitlab ACL)
- Migrate repositories (piece of cake to do by hand, + redmine allows multiple
  repositories per project where gitlab do not)
- Migrate wikis (because we don't care for ourservelves)
- Migrate globally (all projects), because namespacing is different in redmine and gitlab
- Archive your redmine project
- Keep creation/edit dates as metadata.
- Keeps "watchers" on tickets (gitlab API v3 doe not expose it)
- Keeps date/times as metadata
- Keeps track of issue relations orientation

Requires
--------

- Admin token on redmine
- Admin token on gitlab
- No preexisting issues on gitlab project
- Already synced users (those required in the project you are migrating)
- Already existing repository

TODO
----

- Issues relations
- migration of roadmaps
- Keeps who closed
- clarify body note (change API/test)
- Do a script to migrate issue numbers (iid) using a sql connection
- Make --check effective

Let's go
--------

You can or can not use
[virtualenvs](http://docs.python-guide.org/en/latest/dev/virtualenvs/), that's up to you.

Install it:

    ./setup.py install

You can then give it a check without touching anything:

    migrate-redmine-to-gitlab --redmine-key xxxx --gitlab-key xxxx \
      <redmine project url> <gitlab project url> --check

Remove the `--check` to do perform migrations, or better, read:

    migrate-redmine-to-gitlab --help
