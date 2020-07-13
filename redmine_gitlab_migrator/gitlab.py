import re
import logging
import requests
from . import APIClient, Project
import urllib
from urllib.request import urlopen

from redmine_gitlab_migrator.converters import redmine_username_to_gitlab_username

from json.decoder import JSONDecodeError

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

    def get_group_members(self, group_id):
        return self.api.get('{}/groups/{}/members'.format(self.url, group_id))


    def check_users_exist(self, usernames):
        """ Returns True if all users exist
        """
        gitlab_user_names = set([i['username'] for i in self.get_all_users()])

        translated = []
        for i in usernames:
            print(i, redmine_username_to_gitlab_username(i))
            translated.append(redmine_username_to_gitlab_username(i))
        return all((i in gitlab_user_names for i in translated))


class GitlabProject(Project):
    REGEX_PROJECT_URL = re.compile(
        r'^(?P<base_url>https?://[^/]+/)(?P<namespace>[\.\w\._/-]+)/(?P<project_name>[\w\._-]+)$')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group_id = None

        self.instance_url = '{}/api/v4'.format(
            self._url_match.group('base_url'))

        # fetch project_id via api, thanks to lewicki-pk
        # https://github.com/oasiswork/redmine-gitlab-migrator/pull/2
        # but also take int account, that there might be the same project in different namespaces
        path_with_namespace = (
            '{namespace}/{project_name}'.format(
                **self._url_match.groupdict()))
        projectId = -1
        groupId = None

        projects_info = self.api.get('{}/projects?owned=true'.format(self.instance_url))

        for project_attributes in projects_info:
            if project_attributes.get('path_with_namespace') == path_with_namespace:
                projectId = project_attributes.get('id')
                if project_attributes.get('namespace').get('kind') == 'group':
                    groupId = project_attributes.get('namespace').get('id')

        self.project_id = projectId
        if projectId == -1 :
            raise ValueError('Could not get project_id for path_with_namespace: {}'.format(path_with_namespace))
        if groupId:
            self.group_id = groupId

        self.api_url = (
            '{base_url}api/v4/projects/'.format(
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

           files = []
           try:
               files = [("file", (u['filename'], urlopen(u['content_url']), u['content_type']))]
           except urllib.error.HTTPError as e:
               log.warn("{} can't upload due to error: {}!".format(u['content_url'], e))


           try:
               upload = self.api.post(
                   uploads_url, files=files)
               l.append('{} {}'.format(upload['markdown'], u['description']))

           except requests.exceptions.HTTPError:
               # gitlab might throw an "ArgumentError (invalid byte sequence in UTF-8)" in production.log
               # if the filename contains special chars like german "umlaute"
               # in that case we retry with an ascii only filename.
               try:
                   files = [("file", (self.remove_non_ascii(u['filename']), urlopen(u['content_url']), u['content_type']))]
                   upload = self.api.post(uploads_url, files=files)
                   l.append('{} {}'.format(upload['markdown'], u['description']))
               except urllib.error.HTTPError as e:
                   log.warn("{} can't upload due to error: {}!".format(u['content_url'], e))


        return "\n  * ".join(l)

    def remove_non_ascii(self, text):
        # http://stackoverflow.com/a/20078869/98491
        return ''.join([i if ord(i) < 128 else ' ' for i in text])

    def create_issue(self, data, meta, auth_header):
        """ High-level issue creation

        :param meta: dict with "sudo_user", "must_close", "notes" and "attachments" keys
        :param data: dict formatted as the gitlab API expects it
        :param auth_header: dict to with headers to auth request
        :return: the created issue (without notes)
        """

        # attachments have to be uploaded prior to creating an issue
        # attachments are not related to an issue but can be referenced instead
        # see: https://docs.gitlab.com/ce/api/projects.html#upload-a-file
        uploads_text = self.uploads_to_string(meta['uploads'])
        if len(uploads_text) > 0:
           data['description'] = "{}\n* Uploads:\n  * {}".format(data['description'], uploads_text)
        headers = auth_header
        if 'sudo_user' in meta:
            headers['SUDO'] = meta['sudo_user']
        issues_url = '{}/issues'.format(self.api_url)
        issue = None
        try:
            issue = self.api.post(
                issues_url, data=data, headers=headers)
        except requests.exceptions.HTTPError as e:
            log.error("Can't convert issue due to error: {}".format(e.response.content))
            exit()


        issue_url = '{}/{}'.format(issues_url, issue['iid'])

        # Handle issues notes
        issue_notes_url = '{}/notes'.format(issue_url, 'notes')
        for note_data, note_meta in meta['notes']:
            note_headers = auth_header
            if 'sudo_user' in note_meta:
                note_headers['SUDO'] = note_meta['sudo_user']
            self.api.post(
                issue_notes_url, data=note_data,
                headers=note_headers)

        # Handle estimated and spent time
        if meta['human_time_estimate'] is not None and meta['human_time_estimate'] != 0.0:
            time_estimate_url = '{}/time_estimate?duration={}h'.format(issue_url, meta['human_time_estimate'])
            self.api.post(time_estimate_url)
        if meta['human_total_time_spent'] is not None and meta['human_total_time_spent'] != 0.0:
            time_spent_url = '{}/add_spent_time?duration={}h'.format(issue_url, meta['human_total_time_spent'])
            self.api.post(time_spent_url)

        # Handle closed status
        if meta['must_close']:
            self.api.put(issue_url, {'state_event': 'close'})

        return issue

    def delete_issue(self, iid):
        issue_url = '{}/issues/{}'.format(self.api_url, iid)
        try:
            self.api.delete(issue_url)
        except JSONDecodeError:
            True

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
        project_members = self.api.get('{}/members'.format(self.api_url))
        if self.group_id:
            group_members = self.get_instance().get_group_members(self.group_id)
            return project_members + group_members
        else:
            return project_members

    def get_members_index(self):
        """ Returns dict index of users (by login)
        """
        return {i['username']: i for i in self.get_members()}

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

