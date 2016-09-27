import re
import logging
import requests

from . import APIClient, Project
from urllib.request import urlopen

log = logging.getLogger(__name__)

class GitlabClient(APIClient):
    # see http://doc.gitlab.com/ce/api/#pagination
    MAX_PER_PAGE = 100

    def get(self, *args, **kwargs):
        kwargs['params'] = kwargs.get('params', {})
        kwargs['params']['page'] = 1
        kwargs['params']['per_page'] = self.MAX_PER_PAGE

        result = super().get(*args, **kwargs)
        while (len(result) > 0 and len(result) % self.MAX_PER_PAGE == 0):
            kwargs['params']['page'] += 1
            result.extend(super().get(*args, **kwargs))	
        return result 

    def get_auth_headers(self):
        return {"PRIVATE-TOKEN": self.api_key}

    def check_is_admin(self):
        pass


class GitlabInstance:
    def __init__(self, url, client):
        self.url = url.strip('/')  # normalize URL
        self.api = client

    def get_all_users(self):
        return self.api.get('{}/users'.format(self.url))

    def get_users_index(self):
        """ Returns dict index of users (by login)
        """
        return {i['username']: i for i in self.get_all_users()}

    def check_users_exist(self, usernames):
        """ Returns True if all users exist
        """
        gitlab_user_names = set([i['username'] for i in self.get_all_users()])
        return all((i in gitlab_user_names for i in usernames))


class GitlabProject(Project):
    REGEX_PROJECT_URL = re.compile(
        r'^(?P<base_url>https?://.*/)(?P<namespace>[\w_-]+)/(?P<project_name>[\w_-]+)$')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.instance_url = '{}/api/v3'.format(
            self._url_match.group('base_url'))

        # fetch project_id via api, thanks to lewicki-pk 
        # https://github.com/oasiswork/redmine-gitlab-migrator/pull/2
        # but also take int account, that there might be the same project in different namespaces
        path_with_namespace = (
            '{namespace}/{project_name}'.format(
                **self._url_match.groupdict())) 
        projectId = -1

        projects_info = self.api.get('{}/projects'.format(self.instance_url))
 
        for project_attributes in projects_info:
            if project_attributes.get('path_with_namespace') == path_with_namespace:
                projectId = project_attributes.get('id')

        self.project_id = projectId
        if projectId == -1 :
            raise ValueError('Could not get project_id for path_with_namespace: {}'.format(path_with_namespace))

        self.api_url = (
            '{base_url}api/v3/projects/'.format(
                **self._url_match.groupdict())) + str(projectId)


    def is_repository_empty(self):
        """ Heuristic to check if repository is empty
        """
        return self.api.get(self.api_url)['default_branch'] is None

    def uploads_to_string(self, uploads):

        uploads_url = '{}/uploads'.format(self.api_url)
        l = []
        for u in uploads:

           log.info('\tuploading {} ({} / {})'.format(u['filename'], u['content_url'], u['content_type']))

           # http://docs.python-requests.org/en/latest/user/quickstart/#post-a-multipart-encoded-file 
           # http://stackoverflow.com/questions/20830551/how-to-streaming-upload-with-python-requests-module-include-file-and-data
           files = [("file", (u['filename'], urlopen(u['content_url']), u['content_type']))]

           try:
               upload = self.api.post(
                   uploads_url, files=files)
           except requests.exceptions.HTTPError:
               # gitlab might throw an "ArgumentError (invalid byte sequence in UTF-8)" in production.log
               # if the filename contains special chars like german "umlaute"
               # in that case we retry with an ascii only filename. 
               files = [("file", (self.remove_non_ascii(u['filename']), urlopen(u['content_url']), u['content_type']))]
               upload = self.api.post(
                   uploads_url, files=files)

           l.append('{} {}'.format(upload['markdown'], u['description']))

        return "\n  * ".join(l)

    def remove_non_ascii(self, text):
        # http://stackoverflow.com/a/20078869/98491
        return ''.join([i if ord(i) < 128 else ' ' for i in text])

    def create_issue(self, data, meta):
        """ High-level issue creation

        :param meta: dict with "sudo_user", "must_close", "notes" and "attachments" keys
        :param data: dict formatted as the gitlab API expects it
        :return: the created issue (without notes)
        """

        # attachments have to be uploaded prior to creating an issue
        # attachments are not related to an issue but can be referenced instead
        # see: https://docs.gitlab.com/ce/api/projects.html#upload-a-file
        uploads_text = self.uploads_to_string(meta['uploads'])
        if len(uploads_text) > 0:
           data['description'] = "{}\n* Uploads:\n  * {}".format(data['description'], uploads_text)

        issues_url = '{}/issues'.format(self.api_url)
        issue = self.api.post(
            issues_url, data=data, headers={'SUDO': meta['sudo_user']})

        issue_url = '{}/{}'.format(issues_url, issue['id'])

        # Handle issues notes
        issue_notes_url = '{}/notes'.format(issue_url, 'notes')
        for note_data, note_meta in meta['notes']:
            self.api.post(
                issue_notes_url, data=note_data,
                headers={'SUDO': note_meta['sudo_user']})

        # Handle closed status
        if meta['must_close']:
            altered_issue = issue.copy()
            altered_issue['state_event'] = 'close'
            self.api.put(issue_url, data=altered_issue)

        return issue

    def create_milestone(self, data, meta):
        """ High-level milestone creation

        :param meta: dict with "should_close"
        :param data: dict formatted as the gitlab API expects it
        :return: the created milestone
        """
        milestones_url = '{}/milestones'.format(self.api_url)

        # create milestone if not exists
        try:
            milestone = self.get_milestone_by_title(data['title'])
        except ValueError:
            milestone = self.api.post(milestones_url, data=data)

        if (meta['must_close'] and milestone['state'] != 'closed'):
            milestone_url = '{}/{}'.format(milestones_url, milestone['id'])
            altered_milestone = milestone.copy()
            altered_milestone['state_event'] = 'close'

            self.api.put(milestone_url, data=altered_milestone)
        return milestone

    def get_issues(self):
        return self.api.get('{}/issues'.format(self.api_url))

    def get_members(self):
        return self.api.get('{}/members'.format(self.api_url))

    def get_milestones(self):
        if not hasattr(self, '_cache_milestones'):
            self._cache_milestones = self.api.get(
                '{}/milestones'.format(self.api_url))
        return self._cache_milestones

    def get_milestones_index(self):
        return {i['title']: i for i in self.get_milestones()}

    def get_milestone_by_id(self, _id):
        milestones = self.get_milestones()
        for i in milestones:
            if i['id'] == _id:
                return i
        raise ValueError('Could not get milestone for id {}'.format(_id))

    def get_milestone_by_title(self, _title):
        milestones = self.get_milestones()
        for i in milestones:
            if i['title'] == _title:
                return i
        raise ValueError('Could not get milestone for title {}'.format(_title))

    def has_members(self, usernames):
        gitlab_user_names = set([i['username'] for i in self.get_members()])
        return all((i in gitlab_user_names for i in usernames))

    def get_id(self):
        return self.api.get(self.api_url)['id']

    def get_instance(self):
        """ Return a GitlabInstance
        """
        return GitlabInstance(self.instance_url, self.api)

