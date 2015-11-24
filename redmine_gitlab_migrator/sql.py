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


MIGRATE_IID_ISSUES = r"""
UPDATE issues SET
  title = regexp_replace(issues.title, '{regex}','\2'),
  iid = regexp_replace(issues.title, '{regex}', '\1')::integer
WHERE title ~* '{regex}' AND project_id={project_id};
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
