#!/bin/env python3
import argparse
import logging
import re
import sys

from redmine_gitlab_migrator.redmine import RedmineProject, RedmineClient
from redmine_gitlab_migrator.gitlab import GitlabProject, GitlabClient
from redmine_gitlab_migrator.converters import convert_issue, convert_version
from redmine_gitlab_migrator.logging import setup_module_logging
from redmine_gitlab_migrator import sql


"""Migration commands for issues and roadmaps from redmine to gitlab
"""

log = logging.getLogger(__name__)


class CommandError(Exception):
    """ An error that will nicely pop up to user and stops program
    """
    def __init__(self, msg):
        self.msg = msg


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)

    subparsers = parser.add_subparsers(dest='command')

    parser_issues = subparsers.add_parser(
        'issues', help=perform_migrate_issues.__doc__)
    parser_issues.set_defaults(func=perform_migrate_issues)

    parser_roadmap = subparsers.add_parser(
        'roadmap', help=perform_migrate_roadmap.__doc__)
    parser_roadmap.set_defaults(func=perform_migrate_roadmap)

    parser_iid = subparsers.add_parser(
        'iid', help=perform_migrate_iid.__doc__)
    parser_iid.set_defaults(func=perform_migrate_iid)

    for i in (parser_issues, parser_roadmap):
        i.add_argument('redmine_project_url')
        i.add_argument(
            '--redmine-key',
            required=True,
            help="Redmine administrator API key")

    for i in (parser_issues, parser_roadmap, parser_iid):
        i.add_argument('gitlab_project_url')
        i.add_argument(
            '--gitlab-key',
            required=True,
            help="Gitlab administrator API key")

        i.add_argument(
            '--check',
            required=False, action='store_true', default=False,
            help="do not perform any action, just check everything is ready")

        i.add_argument(
            '--debug',
            required=False, action='store_true', default=False,
            help="More output")

    return parser.parse_args()


def check(func, message, redmine_project, gitlab_project):
    ret = func(redmine_project, gitlab_project)
    if ret:
        log.info('{}... OK'.format(message))
    else:
        log.error('{}... FAILED'.format(message))
        exit(1)


def check_users(redmine_project, gitlab_project):
    users = redmine_project.get_participants()
    # Filter out anonymous user
    nicks = [i['login'] for i in users if i['login'] != '']
    log.info('Project users are: {}'.format(', '.join(nicks) + ' '))

    return gitlab_project.get_instance().check_users_exist(nicks)


def check_no_issue(redmine_project, gitlab_project):
    return len(gitlab_project.get_issues()) == 0


def check_no_milestone(redmine_project, gitlab_project):
    return len(gitlab_project.get_milestones()) == 0


def check_origin_milestone(redmine_project, gitlab_project):
    return len(redmine_project.get_versions()) > 0


def perform_migrate_issues(args):
    redmine = RedmineClient(args.redmine_key)
    gitlab = GitlabClient(args.gitlab_key)

    redmine_project = RedmineProject(args.redmine_project_url, redmine)
    gitlab_project = GitlabProject(args.gitlab_project_url, gitlab)

    gitlab_instance = gitlab_project.get_instance()

    gitlab_users_index = gitlab_instance.get_users_index()
    redmine_users_index = redmine_project.get_users_index()

    checks = [
        (check_users, 'Required users presence'),
        (check_no_issue, 'Project has no pre-existing issue'),
    ]
    for i in checks:
        check(
            *i, redmine_project=redmine_project, gitlab_project=gitlab_project)

    # Get issues

    issues = redmine_project.get_all_issues()
    milestones_index = gitlab_project.get_milestones_index()
    issues_data = (
        convert_issue(
            i, redmine_users_index, gitlab_users_index, milestones_index)
        for i in issues)

    for data, meta in issues_data:
        if args.check:
            milestone_id = data.get('milestone_id', None)
            if milestone_id:
                try:
                    gitlab_project.get_milestone_by_id(milestone_id)
                except ValueError:
                    raise CommandError(
                        "issue \"{}\" points to unknown milestone_id \"{}\". "
                        "Check that you already migrated roadmaps".format(
                            data['title'], milestone_id))

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
                r'\s*(\d+)\s*', output,
                re.DOTALL | re.MULTILINE)
            migrated_count = int(m.group(1))
            log.info('Migrated successfully iid for {} issues'.format(
                migrated_count))
        except (IndexError, AttributeError):
            raise ValueError(
                'Invalid output from postgres command: "{}"'.format(output))


def perform_migrate_roadmap(args):
    redmine = RedmineClient(args.redmine_key)
    gitlab = GitlabClient(args.gitlab_key)

    redmine_project = RedmineProject(args.redmine_project_url, redmine)
    gitlab_project = GitlabProject(args.gitlab_project_url, gitlab)

    checks = [
        (check_no_milestone, 'Gitlab project has no pre-existing milestone'),
        (check_origin_milestone, 'Redmine project contains versions'),
    ]
    for i in checks:
        check(
            *i, redmine_project=redmine_project,
            gitlab_project=gitlab_project)

    versions = redmine_project.get_versions()
    versions_data = (convert_version(i) for i in versions)

    for data, meta in versions_data:
        if args.check:
            log.info("Would create version {}".format(data))
        else:
            created = gitlab_project.create_milestone(data, meta)
            log.info("Version {}".format(created['title']))


def main():
    args = parse_args()

    if hasattr(args, 'func'):
        if args.debug:
            loglevel = logging.DEBUG
        else:
            loglevel = logging.INFO

        # Configure global logging
        setup_module_logging('redmine_gitlab_migrator', level=loglevel)
        try:
            args.func(args)

        except CommandError as e:
            log.error(e)
            exit(12)
