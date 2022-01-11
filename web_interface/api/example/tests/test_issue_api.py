from random import randint

from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.job.models import Job
from web_interface.apps.report.models import Issue
from web_interface.apps.task.models import Task
from web_interface.apps.framework_data.models import TestResults


class IssueViewSetTestCase(CommonAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_results = TestResults.objects.create()
        self.job = Job.objects.create(
            name='testJob', test_list=['test_fake_ok'], project=self.project, creator=self.super_user
        )
        self.task = Task.objects.create(
            target_job=self.job, status=Task.RUNNING, message='testMessage', test_results=self.test_results
        )
        self.issue = Issue.objects.create(
            err_id='testErrId', test_results=self.test_results, wcag='testWCAG', is_best_practice=True, priority='Major'
        )

    def tearDown(self) -> None:
        self.issue.delete()
        self.task.delete()
        self.job.delete()
        self.test_results.delete()
        super().tearDown()

    def test_issue_list(self):
        url = reverse('api:issue-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'][0]['id'], self.issue.id)
        self.assertEqual(response.json()['results'][0]['wcag'], self.issue.wcag)

    def test_issue_retrieve(self):
        url = reverse('api:issue-detail', args=(self.issue.id,))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['id'], self.issue.id)
        self.assertEqual(response.json()['wcag'], self.issue.wcag)

    def test_issue_priorities(self):
        url = reverse('api:issue-priorities')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.issue.priority, response.json())

    def test_issue_create(self):
        url = reverse('api:issue-list')
        issue_name = f'testCreated_{randint(0, 512)}'
        data = {
            'name': issue_name,
            'test_results': self.test_results.id,
            'err_id': 'test_err_id',
            'wcag': 'test_wsag',
            'is_best_practice': False
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        issue_id = response.json()['id']
        self.assertEqual(Issue.objects.get(id=issue_id).name, issue_name)

    def test_issue_update(self):
        url = reverse('api:issue-detail', args=(self.issue.id,))
        issue_name = f'testUpdated_{randint(0, 512)}'
        data = {
            'name': issue_name,
            'test_results': self.test_results.id,
            'err_id': 'test_err_id',
            'wcag': 'test_wsag',
            'is_best_practice': False
        }

        response = self.client.put(url, data=data, format='json')
        self.issue.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.issue.name, issue_name)

    def test_issue_partial_update(self):
        url = reverse('api:issue-detail', args=(self.issue.id,))
        issue_name = f'testPartiallyUpdated_{randint(0, 512)}'
        data = {
            'name': issue_name
        }
        response = self.client.patch(url, data=data, format='json')
        self.issue.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.issue.name, issue_name)

    def test_issue_destroy(self):
        url = reverse('api:issue-detail', args=(self.issue.id,))
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Issue.objects.all().count())
