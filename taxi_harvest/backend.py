from __future__ import unicode_literals

from datetime import datetime
from functools import wraps
import logging

import arrow
import requests
from slugify import slugify

from taxi.aliases import aliases_database
from taxi.backends import BaseBackend, PushEntryFailed
from taxi.exceptions import TaxiException
from taxi.projects import Activity, Project

logger = logging.getLogger(__name__)


class HarvestBackend(BaseBackend):
    def __init__(self, *args, **kwargs):
        super(HarvestBackend, self).__init__(*args, **kwargs)

        self.__headers = {
            'Accept': 'application/json',
        }

        if not self.path.startswith('/'):
            self.path = '/' + self.path

        self._session = requests.Session()

    def get_full_url(self, url):
        return 'https://{host}{url}'.format(
            host=self.hostname, url=url
        )

    def push_entry(self, date, entry):
        return
        post_url = self.get_full_url('/timesheet/create/.json')

        mapping = aliases_database[entry.alias]
        parameters = {
            'time':         entry.hours,
            'project_id':   mapping.mapping[0],
            'activity_id':  mapping.mapping[1],
            'day':          date.day,
            'month':        date.month,
            'year':         date.year,
            'description':  entry.description,
        }

        response = self._session.post(post_url, data=parameters).json()

        if 'exception' in response:
            error = response['exception']['message']
            raise PushEntryFailed(error)
        elif 'error' in response['command']:
            error = None
            for element in response['command']['error']:
                if 'Project' in element:
                    error = element['Project']
                    break

            if not error:
                error = "Unknown error message"

            raise PushEntryFailed(error)

    def get_activities(self):
        activities = self._request(path='/tasks')
        return {a['task']['id']: a['task'] for a in activities}

    def get_projects(self):
        projects = self._request(path='/projects')
        activities_dict = self.get_activities()

        projects_list = []

        for project in projects:
            project = project['project']

            if not project['code']:
                continue

            p = Project(
                    int(project['id']), project['name'],
                    {
                        True: Project.STATUS_ACTIVE,
                        False: Project.STATUS_FINISHED
                    }[project['active']],
                    project['notes'],
                    project['budget']
            )

            if project['starts_on']:
                p.start_date = arrow.get(project['starts_on']).date()

            if project['ends_on']:
                p.start_date = arrow.get(project['ends_on']).date()

            activities = self._request(path='/projects/%s/task_assignments' % project['id'])

            for activity in activities:
                activity = activity['task_assignment']
                try:
                    a = Activity(int(activity['id']),
                                 activities_dict[activity['task_id']]['name'],
                                 activity['hourly_rate'])
                    p.add_activity(a)
                except ValueError:
                    logger.warn(
                        "Cannot import activity %s for project %s because "
                        "activity id is not an int" % (activity, p.id)
                    )

                activity_alias = '%s_%s' % (
                    project['code'],
                    slugify(activities_dict[activity['task_id']]['name'],
                            separator='_')
                )
                p.aliases[activity_alias] = activity['id']

            projects_list.append(p)

        return projects_list

    def _request(self, path='/', method='get', data=None):
        kwargs = {
            'method'  : method,
            'url'     : self.get_full_url(path),
            'headers' : self.__headers,
            'data'    : data,
        }
        kwargs['auth'] = (self.username, self.password)

        resp = self._session.request(**kwargs)

        try:
            return resp.json()
        except ValueError:
            print(resp.content)
            raise
