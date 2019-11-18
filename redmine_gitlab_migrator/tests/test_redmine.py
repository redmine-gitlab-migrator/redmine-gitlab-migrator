import unittest

from .fake import FakeRedmineClient
from redmine_gitlab_migrator.redmine import RedmineProject


class RedmineTestCase(unittest.TestCase):
    def setUp(self):
        self.client = FakeRedmineClient()

    def test_get_issues(self):
        project = RedmineProject(
            'http://localhost:9000/projects/diaspora-site',
            self.client)
        issues = project.get_all_issues()
        self.assertEqual(len(issues), 2)
        self.assertEqual(len(issues[0].get('journals', [])), 0)
        self.assertEqual(len(issues[1].get('journals', [])), 2)

    def test_get_participants(self):
        project_1 = RedmineProject(
            'http://localhost:9000/projects/diaspora-site',
            self.client)

        project_2 = RedmineProject(
            'http://localhost:9000/projects/puppet',
            self.client)

        self.assertEqual(len(project_1.get_participants()), 1)
        self.assertIn('@', project_1.get_participants()[0]['mail'])
        self.assertEqual(len(project_2.get_participants()), 0)

    def test_get_versions(self):
        project = RedmineProject(
            'http://localhost:9000/projects/diaspora-site',
            self.client)
        self.assertEqual(len(project.get_versions()), 2)

    def test_category_url_canonicalized(self):
        project = RedmineProject(
            'http://localhost:9000/project/diaspora/diaspora-site',
            self.client)
        self.assertEqual(
            project.public_url, 'http://localhost:9000/projects/diaspora-site')
