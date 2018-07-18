JOHN = {
    "id": 1,
    "username": "john_smith",
    "name": "John Smith",
    "state": "active",
    "avatar_url":
    "http://localhost:3000/uploads/user/avatar/1/cd8.jpeg",
}
JACK = {
    "id": 2,
    "username": "jack_smith",
    "name": "Jack Smith",
    "state": "blocked",
    "avatar_url": "http://gravatar.com/../e32131cd8.jpeg",
}


REDMINE_ISSUE_1732 = {
    "closed_on": "2015-09-09T15:54:49Z",
    "updated_on": "2015-09-09T15:54:49Z",
    "created_on": "2015-08-21T13:29:41Z",
    "custom_fields": [],
    "done_ratio": 100,
    "start_date": "2015-08-21",
    "description": "The doc is a bit old",
    "subject": "Update doc for v1",
    "assigned_to": {
        "name": "John Smith",
        "id": 83
    },
    "author": {
        "name": "Jack Smith",
        "id": 3
    },
    "priority": {
        "name": "Urgent",
        "id": 6
    },
    "status": {
        "name": "Fixed",
        "id": 3
    },
    "tracker": {
        "name": "Evolution",
        "id": 2
    },
    "project": {
        "name": "Diaspora website",
        "id": 196
    },
    "journals": [
        {
            "id": 3995,
            "user":
            {

                "id": 83,
                "name": "John Smith"
            },
            "notes": "Appliqué par commit commit:66cbf9571ed501c6d38a5978f8a27e7b1aa35268.",
            "created_on": "2015-09-09T13:31:16Z",
            "details":
            [
                {
                    "property": "attr",
                    "name": "status_id",
                    "old_value": "1",
                    "new_value": "2"
                },
                {
                    "property": "attr",
                    "name": "done_ratio",
                    "old_value": "0",
                    "new_value": "50"
                }
            ]
        },
        {
            "id": 4001,
            "user":
            {
                "id": 3,
                "name": "Jack Smith"
            },
            "notes": "",
            "created_on": "2015-09-09T15:54:49Z",
            "details":
            [
                {
                    "property": "attr",
                    "name": "status_id",
                    "old_value": "2",
                    "new_value": "3"
                },
                {
                    "property": "attr",
                    "name": "done_ratio",
                    "old_value": "50",
                    "new_value": "100"
                }
            ]
        }
    ],
    "id": 1732
}


REDMINE_ISSUE_1439 = {
    "id": 1439,
    "updated_on": "2015-04-03T15:24:30Z",
    "created_on": "2015-04-03T14:56:08Z",
    "custom_fields": [],
    "done_ratio": 0,
    "start_date": "2015-04-03",
    "description": "",
    "subject": "Support SSL",
    "author": {
        "name": "John Smith",
        "id": 83
    },
    "watchers": [
        {
            "name": "Jack Smith",
            "id": 3
        }
    ],
    "priority": {
        "name": "Normal",
        "id": 4
    },
    "status": {
        "name": "Nouveau",
        "id": 1
    },
    "tracker": {
        "name": "Evolution",
        "id": 2
    },
    "project": {
        "name": "Diaspora website",
        "id": 196
    },
    "journals": [],
    "relations": [
        {
            "id": 171,
            "issue_id": 1430,
            "issue_to_id": 1439,
            "relation_type": "relates",
            "delay": None
        }
    ],
    "fixed_version": {
        "id": 66,
        "name": "v0.11"
    },

}


class FakeGitlabClient:
    def get(self, url):
        if url.endswith('/users'):
            return [JOHN, JACK]

        elif url.endswith('api/v3/projects'):
            return [{
                "id": 3,
                "description": None,
                "default_branch": "master",
                "public": False,
                "visibility_level": 0,
                "ssh_url_to_repo":
                "git@example.com:diaspora/diaspora-project-site.git",
                "http_url_to_repo":
                "http://example.com/diaspora/diaspora-project-site.git",
                "web_url": "http://example.com/diaspora/diaspora-project-site",
                "tag_list": [
                    "example",
                    "disapora project"
                ],
                "owner": {
                    "id": 3,
                    "name": "Diaspora",
                    "created_at": "2013-09-30T13: 46: 02Z"
                },
                "name": "Diaspora Project Site",
                "name_with_namespace": "Diaspora / Diaspora Project Site",
                "path": "diaspora-project-site",
                "path_with_namespace": "diaspora/diaspora-project-site",
                "issues_enabled": True,
                "merge_requests_enabled": True,
                "wiki_enabled": True,
                "snippets_enabled": False,
                "created_at": "2013-09-30T13: 46: 02Z",
                "last_activity_at": "2013-09-30T13: 46: 02Z",
                "creator_id": 3,
                "namespace": {
                    "created_at": "2013-09-30T13: 46: 02Z",
                    "description": "",
                    "id": 3,
                    "name": "Diaspora",
                    "owner_id": 1,
                    "path": "diaspora",
                    "updated_at": "2013-09-30T13: 46: 02Z"
                },
                "permissions": {
                    "project_access": {
                        "access_level": 10,
                        "notification_level": 3
                    },
                    "group_access": {
                        "access_level": 50,
                        "notification_level": 3
                    }
                },
                "archived": False,
                "avatar_url":
                "http://example.com/uploads/project/avatar/3/uploads/avr.png"
            },
            {
                "id": 6,
                "description": None,
                "default_branch": None,
                "public": False,
                "visibility_level": 0,
                "ssh_url_to_repo": "git@example.com:brightbox/puppet.git",
                "http_url_to_repo": "http://example.com/brightbox/puppet.git",
                "web_url": "http://example.com/brightbox/puppet",
                "tag_list": [
                    "example",
                    "puppet"
                ],
                "owner": {
                    "id": 4,
                    "name": "Brightbox",
                    "created_at": "2013-09-30T13:46:02Z"
                },
                "name": "Puppet",
                "name_with_namespace": "Brightbox / Puppet",
                "path": "puppet",
                "path_with_namespace": "brightbox/puppet",
                "issues_enabled": True,
                "merge_requests_enabled": True,
                "wiki_enabled": True,
                "snippets_enabled": False,
                "created_at": "2013-09-30T13:46:02Z",
                "last_activity_at": "2013-09-30T13:46:02Z",
                "creator_id": 3,
                "namespace": {
                    "created_at": "2013-09-30T13:46:02Z",
                    "description": "",
                    "id": 4,
                    "name": "Brightbox",
                    "owner_id": 1,
                    "path": "brightbox",
                    "updated_at": "2013-09-30T13:46:02Z"
                },
                "archived": False,
                "avatar_url": None
            }]

        elif (url.endswith('/projects/3') or
              url.endswith('/projects/diaspora%2Fdiaspora-project-site')):
            return {
                "id": 3,
                "description": None,
                "default_branch": "master",
                "public": False,
                "visibility_level": 0,
                "ssh_url_to_repo":
                "git@example.com:diaspora/diaspora-project-site.git",
                "http_url_to_repo":
                "http://example.com/diaspora/diaspora-project-site.git",
                "web_url": "http://example.com/diaspora/diaspora-project-site",
                "tag_list": [
                    "example",
                    "disapora project"
                ],
                "owner": {
                    "id": 3,
                    "name": "Diaspora",
                    "created_at": "2013-09-30T13: 46: 02Z"
                },
                "name": "Diaspora Project Site",
                "name_with_namespace": "Diaspora / Diaspora Project Site",
                "path": "diaspora-project-site",
                "path_with_namespace": "diaspora/diaspora-project-site",
                "issues_enabled": True,
                "merge_requests_enabled": True,
                "wiki_enabled": True,
                "snippets_enabled": False,
                "created_at": "2013-09-30T13: 46: 02Z",
                "last_activity_at": "2013-09-30T13: 46: 02Z",
                "creator_id": 3,
                "namespace": {
                    "created_at": "2013-09-30T13: 46: 02Z",
                    "description": "",
                    "id": 3,
                    "name": "Diaspora",
                    "owner_id": 1,
                    "path": "diaspora",
                    "updated_at": "2013-09-30T13: 46: 02Z"
                },
                "permissions": {
                    "project_access": {
                        "access_level": 10,
                        "notification_level": 3
                    },
                    "group_access": {
                        "access_level": 50,
                        "notification_level": 3
                    }
                },
                "archived": False,
                "avatar_url":
                "http://example.com/uploads/project/avatar/3/uploads/avr.png"
            }

        elif (url.endswith('/projects/3/issues') or
              url.endswith('/projects/diaspora%2Fdiaspora-project-site/issues')):
            return [
                {
                    "id": 43,
                    "iid": 3,
                    "project_id": 8,
                    "title": "4xx/5xx pages",
                    "description": "",
                    "labels": [],
                    "milestone": None,
                    "assignee": None,
                    "author": {
                        "id": 1,
                        "username": "john_smith",
                        "email": "john@example.com",
                        "name": "John Smith",
                        "state": "active",
                        "created_at": "2012-05-23T08:00:58Z"
                    },
                    "state": "closed",
                    "updated_at": "2012-07-02T17:53:12Z",
                    "created_at": "2012-07-02T17:53:12Z"
                },
                {
                    "id": 42,
                    "iid": 4,
                    "project_id": 8,
                    "title": "Add user settings",
                    "description": "",
                    "labels": [
                        "feature"
                    ],
                    "milestone": {
                        "id": 1,
                        "title": "v1.0",
                        "description": "",
                        "due_date": "2012-07-20",
                        "state": "reopened",
                        "updated_at": "2012-07-04T13:42:48Z",
                        "created_at": "2012-07-04T13:42:48Z"
                    },
                    "assignee": {
                        "id": 2,
                        "username": "jack_smith",
                        "email": "jack@example.com",
                        "name": "Jack Smith",
                        "state": "active",
                        "created_at": "2012-05-23T08:01:01Z"
                    },
                    "author": {
                        "id": 1,
                        "username": "john_smith",
                        "email": "john@example.com",
                        "name": "John Smith",
                        "state": "active",
                        "created_at": "2012-05-23T08:00:58Z"
                    },
                    "state": "opened",
                    "updated_at": "2012-07-12T13:43:19Z",
                    "created_at": "2012-06-28T12:58:06Z"
                }
            ]

        elif (url.endswith('/projects/3/members') or
              url.endswith('/projects/diaspora%2Fdiaspora-project-site/members')):
            return [JACK, JOHN]

        elif (url.endswith('/projects/6') or
              url.endswith('/projects/brightbox%2Fpuppet')):
            return {
                "id": 6,
                "description": None,
                "default_branch": None,
                "public": False,
                "visibility_level": 0,
                "ssh_url_to_repo": "git@example.com:brightbox/puppet.git",
                "http_url_to_repo": "http://example.com/brightbox/puppet.git",
                "web_url": "http://example.com/brightbox/puppet",
                "tag_list": [
                    "example",
                    "puppet"
                ],
                "owner": {
                    "id": 4,
                    "name": "Brightbox",
                    "created_at": "2013-09-30T13:46:02Z"
                },
                "name": "Puppet",
                "name_with_namespace": "Brightbox / Puppet",
                "path": "puppet",
                "path_with_namespace": "brightbox/puppet",
                "issues_enabled": True,
                "merge_requests_enabled": True,
                "wiki_enabled": True,
                "snippets_enabled": False,
                "created_at": "2013-09-30T13:46:02Z",
                "last_activity_at": "2013-09-30T13:46:02Z",
                "creator_id": 3,
                "namespace": {
                    "created_at": "2013-09-30T13:46:02Z",
                    "description": "",
                    "id": 4,
                    "name": "Brightbox",
                    "owner_id": 1,
                    "path": "brightbox",
                    "updated_at": "2013-09-30T13:46:02Z"
                },
                "archived": False,
                "avatar_url": None
            }
        elif (url.endswith('/projects/6/issues') or
              url.endswith('/projects/brightbox%2Fpuppet/issues')):
            return []

        elif (url.endswith('/projects/6/members') or	
              url.endswith('/projects/brightbox%2Fpuppet/members')):
            return []

        else:
            raise ValueError('No test data for {}'.format(url))


class FakeRedmineClient:
    def unpaginated_get(self, url):
        if '/projects/puppet/issues.json' in url:
            return []

        elif '/projects/diaspora-site/issues.json' in url:
            return [
                {
                    "closed_on": "2015-09-09T15:54:49Z",
                    "updated_on": "2015-09-09T15:54:49Z",
                    "created_on": "2015-08-21T13:29:41Z",
                    "custom_fields": [
                        {
                            "value": "",
                            "name": "Upstream Bug",
                            "id": 2
                        }
                    ],
                    "done_ratio": 100,
                    "start_date": "2015-08-21",
                    "description": "The doc is a bit old",
                    "subject": "Update doc for v1",
                    "assigned_to": {
                        "name": "John Smith",
                        "id": 83
                    },
                    "author": {
                        "name": "Jack Smith",
                        "id": 3
                    },
                    "priority": {
                        "name": "Urgent",
                        "id": 6
                    },
                    "status": {
                        "name": "Fixed",
                        "id": 3
                    },
                    "tracker": {
                        "name": "Evolution",
                        "id": 2
                    },
                    "project": {
                        "name": "Diaspora website",
                        "id": 196
                    },
                    "id": 1732
                },
                {
                    "closed_on": "2015-04-03T15:24:30Z",
                    "updated_on": "2015-04-03T15:24:30Z",
                    "created_on": "2015-04-03T14:56:08Z",
                    "custom_fields": [],
                    "done_ratio": 0,
                    "start_date": "2015-04-03",
                    "description": "",
                    "subject": "Support SSL",
                    "author": {
                        "name": "John Smith",
                        "id": 83
                    },
                    "fixed_version": {
                        "id": 66,
                        "name": "v0.11"
                    },

                    "priority": {
                        "name": "Normal",
                        "id": 4
                    },
                    "status": {
                        "name": "Nouveau",
                        "id": 1
                    },
                    "tracker": {
                        "name": "Evolution",
                        "id": 2
                    },
                    "project": {
                        "name": "Diaspora website",
                        "id": 196
                    },
                    "id": 1439
                },
            ]

        else:
            raise ValueError('{} is unknown data test'.format(url))

    def get(self, url):

        if url.endswith('projects/brightbox/puppet.json'):
            return {
                "project": {
                    "updated_on": "2015-06-11T09:21:13Z",
                    "created_on": "2014-07-23T13:39:19Z",
                    "custom_fields": [],
                    "status": 1,
                    "parent": {
                        "name": "Someother",
                        "id": 186
                    },
                    "homepage": "",
                    "description": "",
                    "identifier": "puppet",
                    "name": "Puppet",
                    "id": 189
                }
            }
        elif '/issues/1732.json' in url:
            return REDMINE_ISSUE_1732

        elif '/issues/1439.json' in url:
            return REDMINE_ISSUE_1439

        elif url.endswith('/projects/diaspora-site.json'):
            return {
                "project": {
                    "updated_on": "2015-06-11T09:20:05Z",
                    "created_on": "2014-09-12T14:34:52Z",
                    "custom_fields": [],
                    "status": 1,
                    "parent": {
                        "name": "wolo",
                        "id": 186
                    },
                    "homepage": "",
                    "description": "Diapspora website on http://diaspora.org",
                    "identifier": "diaspora-site",
                    "name": "Diaspora website",
                    "id": 196,
                }
            }

        elif url.endswith('/projects/diaspora-site/versions.json'):

            return {
                'versions':
                [
                    {
                        "id": 66,
                        "project":
                        {
                            "id": 8,
                            "name": "Diaspora Project Site"
                        },
                        "name": "v0.11",
                        "description": "First-public version",
                        "status": "open",
                        "sharing": "none",
                        "created_on": "2015-11-16T10:11:44Z",
                        "updated_on": "2015-11-16T10:11:44Z"
                    },
                    {
                        "id": 29,
                        "project":
                        {
                            "id": 8,
                            "name": "Diaspora Project Site"
                        },
                        "name": "v0.5",
                        "description": "pre-alpha",
                        "status": "closed",
                        "sharing": "none",
                        "created_on": "2015-04-14T07:53:25Z",
                        "updated_on": "2015-04-20T10:18:15Z"
                    }
                ],
                'total_count': 2,
            }

        elif url.endswith('/users/83.json'):
            return {
                "id": 83,
                "login": "john_smith",
                "firstname": "John",
                "lastname": "Smith",
                "mail": "johnn@example.com",
                "created_on": "2014-06-11T06:54:28Z",
                "last_login_on": "2015-10-09T09:33:10Z"
            }

        elif url.endswith('/users/3.json'):
            return {
                "id": 3,
                "login": "jack_smith",
                "firstname": "Jack",
                "lastname": "Smith",
                "mail": "jack@example.com",
                "created_on": "2014-06-11T06:54:28Z",
                "last_login_on": "2015-10-09T09:33:10Z"
            }

        else:
            raise ValueError('{} is unknown data test'.format(url))
