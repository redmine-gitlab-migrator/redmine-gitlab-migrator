import logging

import requests

# http://stackoverflow.com/a/28002687/98491
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

log = logging.getLogger(__name__)


class APIClient:
    def __init__(self, api_key, verify):
        self.api_key = api_key
        self.verify = verify

    def get_auth_headers(self):
        """ Method to be overloaded by child classes

        :return: a dict with auth headers set
        """
        return {}

    def add_auth_headers(self, kwargs):
        _kwargs = kwargs.copy()
        headers = kwargs.get('headers', {})
        headers.update(self.get_auth_headers())
        _kwargs['headers'] = headers
        _kwargs['verify'] = self.verify
        return _kwargs

    def _req(self, func, *args, **kwargs):
        log.debug('HTTP REQUEST {} {} {}'.format(
            func, args, kwargs))
        kwargs = self.add_auth_headers(kwargs)
        resp = func(*args, **kwargs)
        resp.raise_for_status()
        ret = resp.json()
        log.debug('HTTP RESPONSE {}'.format(ret))
        return ret

    def get(self, *args, **kwargs):
        return self._req(requests.get, *args, **kwargs)

    def post(self, *args, **kwargs):
        return self._req(requests.post, *args, **kwargs)

    def put(self, *args, **kwargs):
        return self._req(requests.put, *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._req(requests.delete, *args, **kwargs)


class Project:
    def __init__(self, url, client):
        self.public_url = url.strip('/')  # normalize URL
        self.api = client

        self._url_match = self.REGEX_PROJECT_URL.match(self.public_url)
        if self._url_match is None:
            raise ValueError(
                '{} is not a valid project URL'.format(url))
