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


def convert_attachment(redmine_issue_attachment, redmine_api_key):
    """ Convert a list of redmine attachments to gitlab uploads

    :param redmine_issue_attachment: a dict describing redmine-api-style attachment
    :param redmine_api_key: the redmine api key used for getting the attachment without logging in
    :return: a dict describing the attachment
    """
    uploads = {
        'filename': redmine_issue_attachment['filename'],
        'description': redmine_issue_attachment.get('description'),
        'content_url': '{}?key={}'.format(redmine_issue_attachment['content_url'], redmine_api_key),
        'content_type': redmine_issue_attachment['content_type']
    }

    return uploads
    

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


def relations_to_string(relations, children, parent_id, issue_id):
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

    for i in children:
        id = i['id']
        tracker = i['tracker']
        
        l.append('{} #{}'.format('child', id))

    if parent_id > 0:
       l.append('{} #{}'.format('parent', parent_id))

    return "\n  * ".join(l)

def changesets_to_string(changesets):
    """ Convert redmine formal changesets to some denormalized string

    :param changesets: list of issues changesets
    :return a string listing changesets.
    """
    l = []
    for i in changesets:
        #log.info(i)
        revision = i['revision']
        user = i['user']['name']
        committed_on = i['committed_on']
        comments = i['comments']

        l.append('Revision {} von {} am {}:\n```\n{}\n```'.format(revision, user, committed_on, comments))

    return "\n  * ".join(l)

def custom_fields_to_string(custom_fields, custom_fields_include):
    """ Convert redmine custom fields to some denormalized string

    :param custom_fields: list of issues custom_fields
    :return a string listing custom_fileds.
    """
    l = []
    for i in custom_fields:
        #log.info(i)
        name = i['name']
        
        if name in custom_fields_include and i.get('value'):
            # Name: Value
            l.append('{}: {}'.format(name, i['value']))

    return "\n  * ".join(l)

# Convertor

def convert_issue(redmine_api_key, redmine_issue, redmine_user_index, gitlab_user_index,
                  gitlab_milestones_index):
   
    closed_states = ['closed', 'rejected', 'erledigt', 'abgewiesen']
    custom_fields_include = ['Kunde']
    issue_state = redmine_issue['status']['name']

    if redmine_issue.get('closed_on', None):
        # quick'n dirty extract date
        close_text = ', closed on {}'.format(redmine_issue['closed_on'][:10])
        closed = True
    elif issue_state.lower() in closed_states:
        close_text = ', closed (state: {})'.format(issue_state)
        closed = True
    else:
        close_text = ''
        closed = False

    #log.info('issue {} {}, state: {}, closed: {}'.format(redmine_issue['id'], redmine_issue['subject'], issue_state, closed))

    relations = redmine_issue.get('relations', [])
    children = redmine_issue.get('children', [])
    parent_id = 0
    if redmine_issue.get('parent', None):
        parent_id = redmine_issue['parent']['id']

    relations_text = relations_to_string(relations, children, parent_id, redmine_issue['id'])
    if len(relations_text) > 0:
        relations_text = "\n* Relations:\n  * " + relations_text

    changesets = redmine_issue.get('changesets', [])
    changesets_text = changesets_to_string(changesets)
    if len(changesets_text) > 0:
        changesets_text = "\n* Changesets:\n  * " + changesets_text

    custom_fields = redmine_issue.get('custom_fields', [])
    custom_fields_text = custom_fields_to_string(custom_fields, custom_fields_include)
    if len(custom_fields_text) > 0:
        custom_fields_text = "\n* Custom Fields:\n  * " + custom_fields_text

    labels = [redmine_issue['tracker']['name']]
    if (redmine_issue.get('category')):
        labels.append(redmine_issue['category']['name'])

    attachments = redmine_issue.get('attachments', [])
  
    data = {
        'title': '-RM-{}-MR-{}'.format(
            redmine_issue['id'], redmine_issue['subject']),
        'description': '{}\n\n*(from redmine: created on {}{})*\n{}{}{}'.format(
            redmine_issue['description'],
            redmine_issue['created_on'][:10],
            close_text,
            relations_text,
            changesets_text,
            custom_fields_text
        ),
        'labels': labels,
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
        'must_close': closed,
        'uploads': (convert_attachment(a, redmine_api_key) for a in attachments)
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
