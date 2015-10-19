import unittest

from .fake import JOHN, JACK, REDMINE_ISSUE_1439, REDMINE_ISSUE_1732
from redmine_gitlab_migrator.converters import (
    convert_issue, relations_to_string)


class ConvertorTestCase(unittest.TestCase):
    def setUp(self):
        self.gitlab_users_idx = {
            'john_smith': JOHN,
            'jack_smith': JACK,
        }

        self.redmine_user_index = {
            83: {
                "id": 83,
                "login": "john_smith",
                "firstname": "John",
                "lastname": "Smith",
                "mail": "johnn@example.com",
                "created_on": "2014-06-11T06:54:28Z",
                "last_login_on": "2015-10-09T09:33:10Z"
            },
            3: {
                "id": 3,
                "login": "jack_smith",
                "firstname": "Jack",
                "lastname": "Smith",
                "mail": "jack@example.com",
                "created_on": "2014-06-11T06:54:28Z",
                "last_login_on": "2015-10-09T09:33:10Z"
            }
        }

    def test_closed_issue(self):
        redmine_issue = REDMINE_ISSUE_1732
        gitlab_issue, meta = convert_issue(
            redmine_issue, self.redmine_user_index, self.gitlab_users_idx)
        self.assertEqual(gitlab_issue, {
            'title': '-RM-1732-MR-Update doc for v1',
            'description': 'The doc is a bit old\n\n*(from redmine: created on 2015-08-21, closed on 2015-09-09)*',
            'labels': ['Evolution'],
            'assignee_id': JOHN['id'],
        })
        self.assertEqual(meta, {
            'sudo_user': JACK['username'],
            'notes': [
                {
                    'sudo': 'john_smith',
                    'body': 'Appliqué par commit commit:66cbf9571ed501c6d38a5978f8a27e7b1aa35268.'
                    '\n\n*(from redmine: written on 2015-09-09)*'
                }
                # empty notes should not be kept
            ],
            'must_close': True
        })

    def test_open_issue(self):
        redmine_issue = REDMINE_ISSUE_1439
        gitlab_issue, meta = convert_issue(
            redmine_issue, self.redmine_user_index, self.gitlab_users_idx)

        self.assertEqual(gitlab_issue, {
            'title': '-RM-1439-MR-Support SSL',
            'description': '\n\n*(from redmine: created on 2015-04-03, relates #1430)*',
            'labels': ['Evolution'],
        })
        self.assertEqual(meta, {
            'sudo_user': JOHN['username'],
            'notes': [],
            'must_close': False
        })

    def test_relations_to_string(self):
        simple_oneway = {
            'issue_id': 2, 'issue_to_id': 3, 'relation_type': 'relates'}
        simple_otherway = {
            'issue_id': 3, 'issue_to_id': 2, 'relation_type': 'ref'}

        self.assertEqual(relations_to_string([], 42), '')
        self.assertEqual(
            relations_to_string([simple_oneway], 2),
            'relates #3')
        self.assertEqual(
            relations_to_string([simple_otherway], 2),
            'ref #3')
        self.assertEqual(
            relations_to_string([simple_oneway, simple_otherway], 2),
            'relates #3, ref #3')
