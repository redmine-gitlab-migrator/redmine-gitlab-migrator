""" Convert Redmine objects to gitlab's
"""

import logging


log = logging.getLogger(__name__)

# Utils


def redmine_uid_to_login(redmine_id, redmine_user_index):
    return redmine_user_index[redmine_id]['login']


def redmine_uid_to_gitlab_uid(redmine_id,
                              redmine_user_index, gitlab_user_index):
    username = redmine_uid_to_login(redmine_id, redmine_user_index)
    return gitlab_user_index[username]['id']


def convert_notes(redmine_issue_journals, redmine_user_index):
    """ Convert a list of redmine journal entries to gitlab notes

    Filters out the empty notes (ex: bare status change)
    Adds metadata as comment

    :param redmine_issue_journals: list of redmine "journals"
    :return: yielded couple ``data``, ``meta``. ``data`` is the API payload for
        an issue note and meta a dict (containing, at the moment, only a
        "sudo_user" key).
    """

    for entry in redmine_issue_journals:
        journal_notes = entry.get('notes', '')
        if len(journal_notes) > 0:
            body = "{}\n\n*(from redmine: written on {})*".format(
                journal_notes, entry['created_on'][:10])
            try:
                author = redmine_uid_to_login(
                    entry['user']['id'], redmine_user_index)
            except KeyError:
                # In some cases you have anonymous notes, which do not exist in
                # gitlab.
                log.warning(
                    'Redmine user {} is unknown, attribute note '
                    'to current admin\n'.format(entry['user']))
                author = None
            yield {'body': body}, {'sudo_user': author}


def relations_to_string(relations, issue_id):
    """ Convert redmine formal relations to some denormalized string

    That's the way gitlab does relations, by "mentioning".

    :param relations: list of issues relations
    :param issue_id: the current issue id
    :return a string listing relations.
    """
    l = []
    for i in relations:
        if issue_id == i['issue_id']:
            other_issue_id = i['issue_to_id']
        else:
            other_issue_id = i['issue_id']
        l.append('{} #{}'.format(i['relation_type'], other_issue_id))

    return ', '.join(l)


# Convertor

def convert_issue(redmine_issue, redmine_user_index, gitlab_user_index,
                  gitlab_milestones_index):
    if redmine_issue.get('closed_on', None):
        # quick'n dirty extract date
        close_text = ', closed on {}'.format(redmine_issue['closed_on'][:10])
        closed = True
    else:
        close_text = ''
        closed = False

    relations = redmine_issue.get('relations', [])
    relations_text = relations_to_string(relations, redmine_issue['id'])
    if len(relations_text) > 0:
        relations_text = ', ' + relations_text

    data = {
        'title': '-RM-{}-MR-{}'.format(
            redmine_issue['id'], redmine_issue['subject']),
        'description': '{}\n\n*(from redmine: created on {}{}{})*'.format(
            redmine_issue['description'],
            redmine_issue['created_on'][:10],
            close_text,
            relations_text
        ),
        'labels': [redmine_issue['tracker']['name']]
    }

    version = redmine_issue.get('fixed_version', None)
    if version:
        data['milestone_id'] = gitlab_milestones_index[version['name']]['id']

    try:
        author_login = redmine_uid_to_login(
            redmine_issue['author']['id'], redmine_user_index)

    except KeyError:
        log.warning(
            'Redmine issue #{} is anonymous, gitlab issue is attributed '
            'to current admin\n'.format(redmine_issue['id']))
        author_login = None

    meta = {
        'sudo_user': author_login,
        'notes': list(convert_notes(redmine_issue['journals'],
                                    redmine_user_index)),
        'must_close': closed
    }

    assigned_to = redmine_issue.get('assigned_to', None)
    if assigned_to is not None:
        data['assignee_id'] = redmine_uid_to_gitlab_uid(
            assigned_to['id'], redmine_user_index, gitlab_user_index)
    return data, meta


def convert_version(redmine_version):
    """ Turns a redmine version into a gitlab milestone

    Do not handle the issues linked to the milestone/version.
    Note that redmine do not expose a due date in API.

    :param redmine_version: a dict describing redmine-api-style version
    :rtype: couple: dict, dict
    :return: a dict describing gitlab-api-style milestone and another for meta
    """
    milestone = {
        "title": redmine_version['name'],
        "description": '{}\n\n*(from redmine: created on {})*'.format(
            redmine_version['description'],
            redmine_version['created_on'][:10])
    }
    if 'due_date' in redmine_version:
        milestone['due_date'] = redmine_version['due_date'][:10]

    must_close = redmine_version['status'] == 'closed'

    return milestone, {'must_close': must_close}
