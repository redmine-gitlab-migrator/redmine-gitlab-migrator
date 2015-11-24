#!/bin/env python3
import argparse
import logging
import re
import sys

from redmine_gitlab_migrator.redmine import RedmineProject, RedmineClient
from redmine_gitlab_migrator.gitlab import GitlabProject, GitlabClient
from redmine_gitlab_migrator.converters import convert_issue
from redmine_gitlab_migrator.logging import setup_module_logging
from redmine_gitlab_migrator import sql


"""Migration commands for issues and roadmaps from redmine to gitlab
"""

log = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("subcommand",
                        choices=('issues', 'roadmap', 'iid'),
                        help='subcommand')
    parser.add_argument('redmine_project_url')
    parser.add_argument('gitlab_project_url')
    parser.add_argument('--redmine-key', required=True,
                        help="Redmine administrator API key")
    parser.add_argument('--gitlab-key', required=True,
                        help="Gitlab administrator API key")
    parser.add_argument('--check', required=False, action='store_true', default=False,
                        help="do not perform any action, just check everything is ready for migration"),
    parser.add_argument(
        '--debug', required=False, action='store_true', default=False,
        help="More output"),
    return parser.parse_args()


def check_users(redmine_project, gitlab_project):
    users = redmine_project.get_participants()
    nicks = [i['login'] for i in users]
    sys.stdout.write(', '.join(nicks)+ ' ')

    return gitlab_project.get_instance().check_users_exist(nicks)


def check_no_issue(redmine_project, gitlab_project):
    return len(gitlab_project.get_issues()) == 0


def check_no_milestone(redmine_project, gitlab_project):
    return len(gitlab_project.get_milestones()) == 0


def perform_migrate_issues(args):
    redmine = RedmineClient(args.redmine_key)
    gitlab = GitlabClient(args.gitlab_key)

    redmine_project = RedmineProject(args.redmine_project_url, redmine)
    gitlab_project = GitlabProject(args.gitlab_project_url, gitlab)

    gitlab_instance = gitlab_project.get_instance()

    gitlab_users_index = gitlab_instance.get_users_index()
    redmine_users_index = redmine_project.get_users_index()

    def check(func, message):
        ret = func(redmine_project, gitlab_project)
        if ret:
            log.info('{}... OK'.format(message))
        else:
            log.error('{}... FAILED'.format(message))
            exit(1)

    check(check_users, 'Required users presence')
    check(check_no_issue, 'Project has no pre-existing issue')
    check(check_no_milestone, 'Project has no pre-existing milestone')

    # Get issues

    issues = redmine_project.get_all_issues()
    issues_data = (convert_issue(i, redmine_users_index, gitlab_users_index)
                   for i in issues)

    for data, meta in issues_data:
        if args.check:
            log.info('Would create issue "{}" and {} notes.'.format(
                data['title'],
                len(meta['notes'])))
        else:
            created = gitlab_project.create_issue(data, meta)
            log.info('#{iid} {title}'.format(**created))


def perform_migrate_iid(args):
    """ Shoud occur after the issues migration
    """

    gitlab = GitlabClient(args.gitlab_key)
    gitlab_project = GitlabProject(args.gitlab_project_url, gitlab)
    gitlab_project_id = gitlab_project.get_id()

    regex_saved_iid = r'-RM-([0-9]+)-MR-(.*)'

    sql_cmd = sql.COUNT_UNMIGRATED_ISSUES.format(
        regex=regex_saved_iid, project_id=gitlab_project_id)

    output = sql.run_query(sql_cmd)

    try:
        m = re.match(r'\s*(\d+)\s*', output, re.DOTALL | re.MULTILINE)
        issues_count = int(m.group(1))
    except (AttributeError, ValueError):
        raise ValueError(
            'Invalid output from postgres command: "{}"'.format(output))

    if issues_count > 0:
        log.info('Ready to recover iid for {} issues.'.format(
            issues_count))
    else:
        log.error(
            "No issue to migrate iid, possible causes: "
            "you already migrated iid or you haven't migrated issues yet.")
        exit(1)

    if not args.check:
        sql_cmd = sql.MIGRATE_IID_ISSUES.format(
            regex=regex_saved_iid, project_id=gitlab_project_id)
        out = sql.run_query(sql_cmd)

        try:
            m = re.match(
                r'\s*UPDATE\s+(\d+)\s*', output, re.DOTALL | re.MULTILINE)
            migrated_count = int(m.group(1))
            log.info('Migrated successfully iid for {} issues'.format(
                migrated_count))

def main():
    args = parse_args()

    if args.debug:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    # Configure global logging
    setup_module_logging('redmine_gitlab_migrator', level=loglevel)

    if args.subcommand == 'issues':
        perform_migrate_issues(args)
    elif args.subcommand == 'iid':
        perform_migrate_iid(args)
    elif args.subcommand == 'roadmap':
        raise NotImplementedError('Not implemented yet')
