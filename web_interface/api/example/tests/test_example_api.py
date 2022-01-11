from random import randint
from unittest import mock

from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.issue.models import Example
from web_interface.apps.job.models import Job
from web_interface.apps.report.models import Issue
from web_interface.apps.task.models import Task
from web_interface.apps.framework_data.models import TestResults


class ExampleViewSetTestCase(CommonAPITestCase):
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
            err_id='testErrId', test_results=self.test_results,
            wcag='testWCAG', is_best_practice=True
        )
        self.example = Example.objects.create(
            err_id='testErrId', test_results=self.test_results, issue=self.issue,
            code_snippet='testCodeSnippet', problematic_element_selector='testProblematicElementSelector'
        )

    def tearDown(self) -> None:
        self.example.delete()
        self.issue.delete()
        self.task.delete()
        self.job.delete()
        self.test_results.delete()
        super().tearDown()

    def test_example_list(self):
        url = reverse('api:example-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'][0]['id'], self.example.id)
        self.assertEqual(response.json()['results'][0]['code_snippet'], self.example.code_snippet)

    def test_example_retrieve(self):
        url = reverse('api:example-detail', args=(self.example.id,))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['id'], self.example.id)
        self.assertEqual(response.json()['code_snippet'], self.example.code_snippet)
        
    def test_example_create(self):
        url = reverse('api:example-list')
        example_note = f'testCreated_{randint(0, 512)}'
        data = {
            'err_id': 'test_err_id',
            'problematic_element_selector': 'test_problematic_element_selector',
            'code_snippet': 'test_code_snippet',
            'note': example_note
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        example_id = response.json()['id']
        self.assertEqual(Example.objects.get(id=example_id).note, example_note)

    def test_example_update(self):
        url = reverse('api:example-detail', args=(self.example.id,))
        example_note = f'testUpdated_{randint(0, 512)}'
        data = {
            'err_id': 'test_err_id',
            'problematic_element_selector': 'test_problematic_element_selector',
            'code_snippet': 'test_code_snippet',
            'note': example_note
        }

        response = self.client.put(url, data=data, format='json')
        self.example.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.example.note, example_note)

    def test_example_partial_update(self):
        url = reverse('api:example-detail', args=(self.example.id,))
        example_note = f'testPartiallyUpdated_{randint(0, 512)}'
        data = {
            'note': example_note
        }
        response = self.client.patch(url, data=data, format='json')
        self.example.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.example.note, example_note)

    def test_example_destroy(self):
        url = reverse('api:example-detail', args=(self.example.id,))
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Example.objects.all().count())

    @mock.patch('web_interface.api.example.views.xlsdata')
    def test_example_metadata(self, mock_obj):
        url = reverse('api:example-metadata', args=(self.example.id,))
        expected_metadata = {
            'WCAG-BP': 'BP',
            'priority': 'Minor',
            'WCAG': '1.3.1'
        }
        mock_obj.get_data_for_issue.return_value = expected_metadata
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_obj.get_data_for_issue.assert_called_with(self.example.err_id)
        self.assertEqual(response.json(), expected_metadata)

    @mock.patch('web_interface.api.example.views.create_new_issue')
    @mock.patch('web_interface.api.example.views.find_issue_for_warn')
    def test_example_find_issue_for_warn(self, find_issue_for_warn_mock_obj, create_new_issue_mock_obj):
        find_issue_for_warn_mock_obj.return_value = None
        create_new_issue_mock_obj.return_value = self.issue
        is_best_practice = True

        url = reverse('api:example-find-issue-for-warn', args=(self.example.id,))
        data = {
            'is_best_practice': is_best_practice
        }
        response = self.client.post(url, data=data, format='json')

        find_issue_for_warn_mock_obj.assert_called_with(
            err_id=self.example.err_id, is_best_practice=is_best_practice, task=self.example.test_results.task
        )
        create_new_issue_mock_obj.assert_called_with(
            err_id=self.example.err_id, task=self.example.test_results.task, force_best_practice=is_best_practice
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['id'], self.issue.id)
