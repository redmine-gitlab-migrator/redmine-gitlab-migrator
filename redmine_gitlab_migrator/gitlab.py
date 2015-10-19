import re

from . import APIClient, Project


class GitlabClient(APIClient):
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
        self.api_url = (
            '{base_url}api/v3/projects/{namespace}%2F{project_name}'.format(
                **self._url_match.groupdict()))
        self.instance_url = '{}/api/v3'.format(
            self._url_match.group('base_url'))

    def is_repository_empty(self):
        """ Heuristic to check if repository is empty
        """
        return self.api.get(self.api_url)['default_branch'] is None

    def create_issue(self, data, meta):
        """ High-level issue creation

        :param meta: dict with "sudo_user", "should_close" and "notes" keys
        :param data: dict formatted as the gitlab API expects it
        :return: the created issue (without notes)
        """
        issues_url = '{}/issues'.format(self.api_url)
        issue = self.api.post(
            issues_url, data=data, headers={'SUDO': meta['sudo_user']})

        issue_url = '{}/{}'.format(issues_url, issue['id'])

        # Handle issues notes
        issue_notes_url = '{}/notes'.format(issue_url, 'notes')
        for note in meta['notes']:
            sudo_user, body = note['sudo'], note['body']

            self.api.post(
                issue_notes_url, data={'body': body},
                headers={'SUDO': sudo_user})

        # Handle closed status
        if meta['must_close']:
            altered_issue = issue.copy()
            altered_issue['state_event'] = 'close'
            self.api.put(issue_url, data=altered_issue)

        return issue

    def get_issues(self):
        return self.api.get('{}/issues'.format(self.api_url))

    def get_members(self):
        return self.api.get('{}/members'.format(self.api_url))

    def get_milestones(self):
        return self.api.get('{}/milestones'.format(self.api_url))

    def has_members(self, usernames):
        gitlab_user_names = set([i['username'] for i in self.get_members()])
        return all((i in gitlab_user_names for i in usernames))

    def get_instance(self):
        """ Return a GitlabInstance
        """
        return GitlabInstance(self.instance_url, self.api)
