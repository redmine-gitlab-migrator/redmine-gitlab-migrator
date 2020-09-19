Redmine to Gitlab migrator
==========================

[![Build Status](https://travis-ci.org/redmine-gitlab-migrator/redmine-gitlab-migrator.svg?branch=master)](https://travis-ci.org/redmine-gitlab-migrator/redmine-gitlab-migrator)

Migrate code projects from Redmine to Gitlab, keeping issues/milestones/metadata

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
  - issue attachements
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
- Keep "watchers" on tickets (gitlab API v3 does not expose it)
- Keep dates/times as metadata
- Keep track of issue relations orientation (no such notion on gitlab)
- Migrate tags ([redmine_tags](https://www.redmine.org/plugins/redmine_tags)
  plugin), as they are not exposed in gitlab API

Requires
--------

- Python >= 3.5
- gitlab >= 7.0
- redmine >= 1.3
- pandoc >= 1.17.0.0
- API token on redmine
- API token on gitlab
- No preexisting issues on gitlab project
- Already synced users (those required in the project you are migrating)

(Original version was developed/tested around redmine 2.5.2, gitlab 8.2.0, python 3.4)
(Updated version was developed/tested around redmine 3.2.0, gitlab 12.3, python 3.6.8)


Let's go
--------

You can or can not use
[virtualenvs](http://docs.python-guide.org/en/latest/dev/virtualenvs/), that's
up to you.

Install it:

    pip install redmine-gitlab-migrator

or latest version from GitHub:

    pip install git+https://github.com/redmine-gitlab-migrator/redmine-gitlab-migrator

or if you cloned the git:

    python setup.py install

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

It doesn't neet to be named the same, you just have to record it's URL (eg:
*https://git.example.com/mygroup/myproject*).

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

If you're using SSL with self signed cerificates and get an *requests.exceptions.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed (_ssl.c:600)* error, you can disable certificate validation with

    --no-verify

Migrate issues get all users in gitlab. If you have many users in your gitlab, e.g. migrating
to gitlab.com, it will be a slow process. You can use --project-members-only to query
project members instead of all users, if corresponding user can't be found in project
members, the issue/comment will be assigned to the gitlab admin user.

    --project-members-only

If you don't have admin access to gitlab instance, e.g. migrating to gitlab.com, sudo_user is not
allowed, so you have to disable sudo with

    --no-sudo

### Migrate Issues ID (iid)

You can retain the issues ID from redmine, **this cannot be done via REST
API**, thus it requires **direct access to the gitlab machine**.

So you have to log in the gitlab machine (eg. via SSH), and then issue the
commad with sufficient rights, from there:

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
wiki page is included in the repo, however not added/commited), and then
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

Unit testing
------------

Use the standard way:

    python setup.py test

Or use whatever test runner you fancy.

Using Docker container
----------------------

### Start up GitLab with migrator

cf. [GitLab Docs](https://docs.gitlab.com/) > Omnibus GitLab Doc > [GitLab Docker images](https://docs.gitlab.com/omnibus/docker/)

    export GITLAB_HOME=$PWD/srv/gitlab
    docker-compose up -d
    docker-compose logs -f  # You can watch logs and stop with Ctrl+C

After starting a container you can access GitLab http://localhost:8081

- Create group/project and users
- Create Access Token

### Migrate with docker-compose command

#### Roadmap

    docker-compose exec migrator \
      migrate-rg roadmap --redmine-key xxxx --gitlab-key xxxx \
      https://redmine.example.com/projects/myproject \
      http://localhost:8081/mygroup/myproject

#### Issues

    docker-compose exec migrator \
      migrate-rg issues --redmine-key xxxx --gitlab-key xxxx \
      https://redmine.example.com/projects/myproject \
      http://localhost:8081/mygroup/myproject

#### Issues ID (iid)

    docker-compose exec migrator \
      migrate-rg iid --gitlab-key xxxx \
      http://localhost:8081/mygroup/myproject

### Export/Import to production system

cf. GitLab Docs
GitLab Docs > User Docs > Projects > Project settings > [Project import/export](https://docs.gitlab.com/ee/user/project/settings/import_export.html)
