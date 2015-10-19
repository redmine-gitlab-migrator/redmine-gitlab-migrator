import requests


class APIClient:
    def __init__(self, api_key):
        self.api_key = api_key

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
        return _kwargs

    def get(self, *args, **kwargs):
        kwargs = self.add_auth_headers(kwargs)

        resp = requests.get(*args, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def post(self, *args, **kwargs):
        kwargs = self.add_auth_headers(kwargs)

        resp = requests.post(*args, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def put(self, *args, **kwargs):
        kwargs = self.add_auth_headers(kwargs)

        resp = requests.put(*args, **kwargs)
        resp.raise_for_status()
        return resp.json()


class Project:
    def __init__(self, url, client):
        self.public_url = url.strip('/')  # normalize URL
        self.api = client

        self._url_match = self.REGEX_PROJECT_URL.match(self.public_url)
        if self._url_match is None:
            raise ValueError(
                '{} is not a valid project URL'.format(url))
