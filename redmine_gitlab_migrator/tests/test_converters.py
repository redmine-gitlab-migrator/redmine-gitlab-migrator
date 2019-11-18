import unittest

from .fake import JOHN, JACK, REDMINE_ISSUE_1439, REDMINE_ISSUE_1732
from redmine_gitlab_migrator.converters import (
    convert_issue, convert_version, relations_to_string)
from redmine_gitlab_migrator.wiki import TextileConverter


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
        redmine_api_key = '<redmine_api_key>'
        redmine_issue = REDMINE_ISSUE_1732
        textile_converter = TextileConverter()
        gitlab_issue, meta, redmine_id = convert_issue(
            redmine_api_key, redmine_issue, self.redmine_user_index, self.gitlab_users_idx, {}, ['closed', 'rejected'], ['customer'],
            textile_converter, False, True, None)
        self.assertEqual(gitlab_issue, {
            'title': '-RM-1732-MR-Update doc for v1',
            'created_at': '2015-08-21T13:29:41Z',
            'description': 'The doc is a bit old\n\n\n*(from redmine: issue id 1732, created on 2015-08-21, closed on 2015-09-09)*\n',
            'labels': 'Evolution,Fixed,Urgent',
            'due_date': None,
            'assignee_id': JOHN['id'],
        })
        self.assertEqual(meta, {
            'notes': [
                ({'body': 'Appliqué par commit '
                  'commit:66cbf9571ed501c6d38a5978f8a27e7b1aa35268.'
                  '\n\n\n*(from redmine: written on 2015-09-09)*',
                  'created_at': '2015-09-09T13:31:16Z'},
                 {'sudo_user': 'john_smith'})
                # empty notes should not be kept
            ],
            'must_close': True,
            'sudo_user': 'jack_smith',
            'uploads': []
        })

    def test_open_issue(self):
        redmine_api_key = '<redmine_api_key>'
        redmine_issue = REDMINE_ISSUE_1439
        milestone_index = {'v0.11': {'id': 3, 'title': 'v0.11'}}
        textile_converter = TextileConverter()
        gitlab_issue, meta, redmine_id = convert_issue(
            redmine_api_key, redmine_issue, self.redmine_user_index, self.gitlab_users_idx,
            milestone_index, ['closed', 'rejected'], ['customer'], textile_converter, False, True, None)

        self.assertEqual(gitlab_issue, {
            'title': '-RM-1439-MR-Support SSL',
            'description': '\n\n\n*(from redmine: issue id 1439, created on 2015-04-03)*\n\n* Relations:\n  * relates #1430',
            'due_date': None,
            'created_at': '2015-04-03T14:56:08Z',
            'labels': 'Evolution,Nouveau,Normal',
            'milestone_id': 3,
        })
        self.assertEqual(meta, {
            'sudo_user': JOHN['username'],
            'notes': [],
            'must_close': False,
            'uploads': []
        })

    def test_open_version(self):
        redmine_version = {
            "id": 66,
            "project": {"id": 8, "name": "Diaspora Project Site"},
            "name": "v0.11",
            "description": "First public version",
            "status": "open",
            "sharing": "none",
            "created_on": "2015-11-16T10:11:44Z",
            "updated_on": "2015-11-16T10:11:44Z"
        }
        gitlab_milestone, meta = convert_version(redmine_version)
        self.assertEqual(gitlab_milestone, {
            "title": "v0.11",
            "description": ("First public version\n\n*"
                            "(from redmine: created on 2015-11-16)*"),
        })
        self.assertEqual(meta, {'must_close': False})

    def test_closed_version(self):
        redmine_version = {
            "id": 66,
            "project": {"id": 8, "name": "Diaspora Project Site"},
            "name": "v0.11",
            "description": "First public version",
            "status": "closed",
            "sharing": "none",
            "created_on": "2015-11-16T10:11:44Z",
            "updated_on": "2015-11-16T10:11:44Z"
        }
        gitlab_milestone, meta = convert_version(redmine_version)
        self.assertEqual(meta, {'must_close': True})

    def test_relations_to_string(self):
        simple_oneway = {
            'issue_id': 2, 'issue_to_id': 3, 'relation_type': 'relates'}
        simple_otherway = {
            'issue_id': 3, 'issue_to_id': 2, 'relation_type': 'ref'}
        children = [
            {'id': 3}, {'id': 4}
        ]

        self.assertEqual(relations_to_string([], [], 0, 42), '')
        self.assertEqual(
            relations_to_string([simple_oneway], [], 0, 2),
            '  * relates #3')
        self.assertEqual(
            relations_to_string([simple_otherway], [], 0, 2),
            '  * ref #3')
        self.assertEqual(
            relations_to_string([simple_oneway, simple_otherway], [], 0, 2),
            '  * relates #3\n  * ref #3')
        self.assertEqual(
            relations_to_string([], children, 0, 2),
            '  * child #3\n  * child #4')
        self.assertEqual(
            relations_to_string([], [], 5, 2),
            '  * parent #5')
