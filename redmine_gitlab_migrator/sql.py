import logging
import subprocess

""" SQL-related work for gitlab DB
"""

log = logging.getLogger(__name__)


COUNT_UNMIGRATED_ISSUES = r"""
SELECT COUNT(*)
FROM issues
WHERE title ~* '{regex}' AND project_id={project_id};
"""

UPDATE_IID_ISSUES = r"""
UPDATE issues SET
  iid = iid * 100000
WHERE title ~* '{regex}' AND project_id={project_id};
"""

MIGRATE_IID_ISSUES = r"""
UPDATE issues SET
  title = regexp_replace(issues.title, '{regex}','\2'),
  title_html = regexp_replace(issues.title_html, '{regex}','\2'),
  iid = regexp_replace(issues.title, '{regex}', '\1')::integer
WHERE title ~* '{regex}' AND project_id={project_id};
"""

# After rewriting the iids we must also advance GitLab's per-project iid
# allocator (the internal_ids table, usage=0 is "issues"). Otherwise the next
# newly-created issue reuses a low iid that will eventually collide with the
# migrated ones. See https://github.com/redmine-gitlab-migrator/redmine-gitlab-migrator/issues/63
#
# The allocator row is keyed by project_id on older GitLab and by the project's
# ProjectNamespace (internal_ids.namespace_id = projects.project_namespace_id)
# on newer GitLab; match either so the fix works across versions.
UPDATE_INTERNAL_ID_ISSUES = r"""
UPDATE internal_ids SET
  last_value = (SELECT MAX(iid) FROM issues WHERE project_id={project_id})
WHERE usage=0 AND (
  project_id={project_id}
  OR namespace_id = (SELECT project_namespace_id FROM projects WHERE id={project_id})
);
"""


def run_query(
        cmd,
        unix_user='gitlab-psql',
        hostname='/var/opt/gitlab/postgresql',
        dbname='gitlabhq_production',
        psql_bin='/opt/gitlab/embedded/bin/psql'):
    """Run a sql command and returns output

    Defaults match omnibus-installed gitlab settings.

    :param cmd: a SQL command, ending with ";"
    :type cmd: str
    :rtype: str
    """

    log.debug('Running SQL command {}'.format(cmd))

    output = subprocess.check_output([
        'sudo', '-u', unix_user,
        psql_bin,
        '-A', '-t',  # supress output fancy
        '-h', hostname,
        '-d', dbname,
    ], input=cmd.encode())
    log.debug('SQL output is "{}"'.format(output.decode()))

    return output.decode()
