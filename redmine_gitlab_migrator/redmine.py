from itertools import chain
import re

from . import APIClient, Project
from requests.exceptions import HTTPError

ANONYMOUS_USER_ID = 2

class RedmineClient(APIClient):
    PAGE_MAX_SIZE = 100

    def get_auth_headers(self):
        return {"X-Redmine-API-Key": self.api_key}

    def get(self, *args, **kwargs):
        # In detail views, redmine encapsulate "foo" typed objects under a
        # "foo" key on the JSON.
        ret = super().get(*args, **kwargs)
        values = ret.values()
        if len(values) == 1:
            return list(values)[0]
        else:
            return ret

    def unpaginated_get(self, *args, **kwargs):
        """ Iterates over API pagination for a given resource list
        """
        kwargs['params'] = kwargs.get('params', {})
        kwargs['params']['limit'] = self.PAGE_MAX_SIZE

        resp = self.get(*args, **kwargs)

        # Try to autofind the top-level key containing
        keys_candidates = (
            set(resp.keys()) - set(['total_count', 'offset', 'limit']))

        assert len(keys_candidates) == 1
        res_list_key = list(keys_candidates)[0]

        result_pages = [resp[res_list_key]]
        if 'offset' not in resp:
            raise ValueError('HTTP response data is not paginated')

        while (resp['total_count'] - resp['offset'] - resp['limit']) > 0:
            kwargs['params']['offset'] = (kwargs['params'].get('offset', 0)
                                          + self.PAGE_MAX_SIZE)
            resp = self.get(*args, **kwargs)
            result_pages.append(resp[res_list_key])
        return chain.from_iterable(result_pages)


class RedmineProject(Project):
    REGEX_PROJECT_URL = re.compile(
        r'^(?P<base_url>https?://.*)/projects/(?P<project_name>[\w_-]+)$')

    REGEX_CATEGORY_PROJECT_URL = re.compile(
        r'^(?P<base_url>https?://.*)/project/(?P<category_name>[\w_-]+)/(?P<project_name>[\w_-]+)/?$')

    def __init__(self, url, *args, **kwargs):
        normalized_url = self._canonicalize_url(url)
        super().__init__(normalized_url, *args, **kwargs)
        self.api_url = '{}.json'.format(self.public_url)
        self.instance_url = self._url_match.group('base_url')

    @classmethod
    def _canonicalize_url(cls, url):
        """ If using caterogies, return the category-less URL

        eg:
          - category URL: https://example.com/project/dev/foobar/
          - category-less URL: https://example.com/projects/foobar/

        API endpoints are reachable only for category-less URLs.
        """
        m = cls.REGEX_CATEGORY_PROJECT_URL.match(url)
        if m:
            return '{base_url}/projects/{project_name}'.format(**m.groupdict())
        else:
            return url

    def get_all_issues(self):

        if not hasattr(self, '_cache_issues'):

            issues = self.api.unpaginated_get(
                '{}/issues.json?subproject_id=1&status_id=*'.format(self.public_url))
            detailed_issues = []
            # It's impossible to get issue history from list view, so get it from
            # detail view...

            for issue_id in sorted(i['id'] for i in issues):
                issue_url = '{}/issues/{}.json?include=journals,watchers,relations,children,attachments,changesets'.format(
                    self.instance_url, issue_id)
                detailed_issues.append(self.api.get(issue_url))

            self._cache_issues = detailed_issues

        return self._cache_issues

    def get_all_pages(self):
        return self.api.get(
            '{}/wiki/index.json'.format(self.public_url))

    def get_page(self, title, version):
        return self.api.get(
            '{}/wiki/{}/{}.json'.format(self.public_url, title, version))

    def get_participants(self):
        """Get participating users (issues authors/owners)

        :return: list of all users participating on issues
        :rtype: list
        """
        user_ids = set()
        users = []

        for i in self.get_all_issues():
            journals = i.get('journals', [])
            for i in chain(i.get('watchers', []),
                           [i['author'], i.get('assigned_to', None)]):

                if i is None or ('name' not in i and 'author' not in i):
                    continue
                user_ids.add(i['id'])
            for entry in journals:
                if not entry.get('notes', None):
                    continue
                user_ids.add(entry['user']['id'])

        for i in user_ids:
            # The anonymous user is not really part of the project...
            # You may want to add Group IDs such as [ANONYMOUS_USER_ID, 324, 234, ...] if necessary
            if i not in [ANONYMOUS_USER_ID]:
                try:
                  users.append(self.api.get('{}/users/{}.json'.format(
                      self.instance_url, i)))
                except HTTPError:
                  print("unable to retrieve user!")

        return users

    def get_users_index(self):
        """ Returns dict index of users (by user id)
        """
        return {i['id']: i for i in self.get_participants()}

    def get_versions(self):
        response = self.api.get('{}/versions.json'.format(self.public_url))
        return response['versions']
