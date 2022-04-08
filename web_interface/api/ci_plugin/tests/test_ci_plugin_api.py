import time
from unittest import mock

from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import SeparatedClientsAPITestCase
from web_interface.apps.framework_data.models import TestResults, Test
from web_interface.apps.job.models import Job
from web_interface.apps.page.models import Page
from web_interface.apps.project.models import Project
from web_interface.apps.task.models import Task


class CIPluginJobViewSetTestCase(SeparatedClientsAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.job = Job.objects.create(
            name='testJob', test_list=['test_fake_ok'], project=self.project, creator=self.super_user
        )
        self.task = Task.objects.create(target_job=self.job, status=Task.QUEUED, message='testMessage')
        self.first_page = Page.objects.create(name='first_testPage', url='testUrl', project=self.project)
        self.second_page = Page.objects.create(name='second_testPage', url='testUrl', project=self.project)

    def tearDown(self) -> None:
        self.task.delete()
        self.job.delete()
        self.first_page.delete()
        self.second_page.delete()
        super().tearDown()

    def test_ci_plugin_job_retrieve(self):
        url = reverse('api:ci-plugin-job-detail', args=(self.job.id,))
        response = self.api_key_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['name'], self.job.name)
        self.assertEqual(response.json()['project'], self.job.project_id)
        self.assertEqual(response.json()['project_name'], self.job.project.name)

    def test_ci_plugin_job_retrieve__401(self):
        project = Project.objects.create(name='testProject', comment='This is a test project')
        job = Job.objects.create(
            name='testJob', test_list=['test_fake_ok'], project=project, creator=self.super_user
        )
        url = reverse('api:ci-plugin-job-detail', args=(job.id,))
        response = self.api_key_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch('web_interface.apps.task.task_functional.callback_progress.request_test_for_job')
    def test_jobs_start_task(self, mock_obj):
        url = reverse('api:ci-plugin-job-start-task', args=(self.job.id,))
        post_data = {'project': self.project.id}

        mock_obj.return_value = {
            'task_id': self.task.id
        }

        response = self.api_key_client.post(url, data=post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_obj.assert_called_with(self.job)
        self.assertIn('id', response.json())
        self.assertIn('celery_task_id', response.json())


class CIPluginTaskViewSetTestCase(SeparatedClientsAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.job = Job.objects.create(
            name='testJob', test_list=['test_fake_ok'], project=self.project, creator=self.super_user
        )
        self.test_results = TestResults.objects.create()
        self.test = Test.objects.create(
            name='testTest', status='testStatus', support_status='testSupport_status',
            problematic_pages='tastProblematic_pages', test_results=self.test_results
        )
        self.task = Task.objects.create(
            target_job=self.job, status=Task.RUNNING, message='testMessage', test_results=self.test_results
        )

    def tearDown(self) -> None:
        self.task.delete()
        self.test.delete()
        self.test_results.delete()
        self.job.delete()
        super().tearDown()

    def test_ci_plugin_task_retrieve(self):
        url = reverse('api:ci-plugin-task-detail', args=(self.task.id,))
        response = self.api_key_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['status'], self.task.status)
        self.assertEqual(response.json()['message'], self.task.message)
        self.assertEqual(response.json()['tests'][0]['status'], self.test.status)
        self.assertEqual(response.json()['tests'][0]['name'], self.test.name)

    @mock.patch('web_interface.apps.task.tasks.abort_task')
    def test_ci_plugin_task_abort_task(self, mock_obj):
        url = reverse('api:ci-plugin-task-abort-task', args=(self.task.id,))
        mock_obj.side_effect = lambda x: None

        response = self.api_key_client.post(url, format='json')
        mock_obj.assert_called_with(self.task)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['status'], 'Task Aborted')
