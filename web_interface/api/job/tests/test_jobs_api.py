from os import environ
from random import randint
from unittest import mock

from django.urls import reverse
from jira import JIRA, JIRAError
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.framework_data.models import TestResults
from web_interface.apps.issue.models import Example
from web_interface.apps.jira.models import JiraIntegrationParams, JiraRootIssue
from web_interface.apps.job.models import Job
from web_interface.apps.page.models import Page
from web_interface.apps.report.models import Issue
from web_interface.apps.task.models import Task


def update_job_length_side_effect(args=None, kwargs=None, **options):
    job_id = kwargs['job_id']
    job = Job.objects.get(id=job_id)
    estimated_testing_time = randint(0, 512)
    job.estimated_testing_time = estimated_testing_time
    job.save()
    return estimated_testing_time


class JobViewSetTestCase(CommonAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.job = Job.objects.create(
            name='testJob', test_list=['test_fake_ok'], project=self.project, creator=self.super_user
        )
        self.task = Task.objects.create(target_job=self.job, status=Task.QUEUED, message='testMessage')
        self.task_2 = Task.objects.create(target_job=self.job, status=Task.RUNNING, message='testMessage2')
        self.first_page = Page.objects.create(name='first_testPage', url='testUrl', project=self.project)
        self.second_page = Page.objects.create(name='second_testPage', url='testUrl', project=self.project)

        self.test_results = TestResults.objects.create()
        self.task_3 = Task.objects.create(target_job=self.job, status=Task.SUCCESS, message='testMessage3',
                                          test_results=self.test_results)
        self.issue = Issue.objects.create(
            err_id='testErrId', test_results=self.test_results, wcag='testWCAG', is_best_practice=False,
            priority='Major'
        )

        self.example = Example.objects.create(
            err_id='testErrId', test_results=self.test_results, issue=self.issue, severity='FAIL',
            code_snippet='testCodeSnippet', problematic_element_selector='testProblematicElementSelector'
        )

        self.jira_integration_params = JiraIntegrationParams.objects.create(
            project=self.job.project,
            host="https://checker-jira-integration-test.atlassian.net",
            username="anna_isaeva@epam.com",
            token=environ.get('JIRA_TEST_TOKEN'),
            jira_project_key="JIO1"
        )

    def tearDown(self) -> None:
        self.task.delete()
        self.task_2.delete()

        self.jira_integration_params.delete()
        self.example.delete()
        self.issue.delete()
        self.task_3.delete()
        self.test_results.delete()

        self.job.delete()
        self.first_page.delete()
        self.second_page.delete()
        super().tearDown()

    def test_jobs_list(self):
        url = reverse('api:jobs-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'][0]['name'], self.job.name)
        self.assertEqual(response.json()['results'][0]['project'], self.job.project_id)
        self.assertEqual(response.json()['results'][0]['project_name'], self.job.project.name)
        self.assertEqual(response.json()['results'][0]['last_task']['id'], self.task.id)

    def test_jobs_retrieve(self):
        url = reverse('api:jobs-detail', args=(self.job.id,))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['name'], self.job.name)
        self.assertEqual(response.json()['project'], self.job.project_id)
        self.assertEqual(response.json()['project_name'], self.job.project.name)
        self.assertEqual(response.json()['last_task']['id'], self.task.id)
        self.assertEqual(response.json()['status'], self.job.status())

    @mock.patch('web_interface.api.job.views.tasks')
    def test_jobs_precalculate_job_length(self, mock_obj):
        url = reverse('api:jobs-precalculate-job-length')
        post_data = {
            'tests': ['test_example'],
            'pages': [self.first_page.id, self.second_page.id]
        }

        mock_obj.precalculate_job_length.return_value = 33
        response = self.client.post(url, data=post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_obj.precalculate_job_length.assert_called_with(['test_example'], [self.first_page.id, self.second_page.id])
        self.assertEqual(response.json()['time'], 33)

    @mock.patch('web_interface.api.job.views.tasks')
    def test_jobs_start_task(self, mock_obj):
        url = reverse('api:jobs-start-task', args=(self.job.id,))
        post_data = {'project': self.project.id}

        mock_obj.request_test_for_job.return_value = {
            'task_id': self.task.id
        }

        response = self.client.post(url, data=post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_obj.request_test_for_job.assert_called_with(self.job)
        self.assertEqual(response.json()['status'], self.task.status)
        self.assertEqual(response.json()['message'], self.task.message)

    def test_jobs_clone(self):
        url = reverse('api:jobs-clone', args=(self.job.id,))
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.json()['id'], self.job.id)
        self.assertEqual(response.json()['name'], f'{self.job.name} (Copy)')

    @mock.patch('web_interface.api.job.serializers.tasks')
    def test_jobs_create(self, mock_obj):
        url = reverse('api:jobs-list')
        job_name = f'testJobCreated_{randint(0, 512)}'
        data = {
            'name': job_name,
            'test_list': 'test_fake_ok',
            'project': self.project.id,
            'creator': self.super_user.id,
            'pages': [self.first_page.id, self.second_page.id],
            'vpat_reports_params': [
                {
                    'type': 'testType',
                    'standart': 'testStandart',
                    'product_type': 'testProductType'
                }
            ]
        }
        mock_obj.update_job_length.apply.side_effect = update_job_length_side_effect

        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_job = Job.objects.get(id=response.json()['id'])
        mock_obj.update_job_length.apply.assert_called_with(kwargs={'job_id': created_job.id})
        self.assertEqual(response.json()['name'], job_name)
        self.assertIsNotNone(response.json()['estimated_testing_time'])
        self.assertEqual(sorted(response.json()['pages']), sorted((self.first_page.id, self.second_page.id)))
        self.assertTrue(Job.objects.all().count())
        self.assertTrue(created_job.vpatreportparams_set.count())

    @mock.patch('web_interface.api.job.serializers.tasks')
    def test_jobs_update(self, mock_obj):
        url = reverse('api:jobs-detail', args=(self.job.id,))
        job_name = f'testJobUpdated_{randint(0, 512)}'
        data = {
            'name': job_name,
            'test_list': 'test_fake_ok',
            'project': self.project.id,
            'creator': self.super_user.id,
            'pages': [self.first_page.id, self.second_page.id]
        }
        mock_obj.update_job_length.apply.side_effect = update_job_length_side_effect

        response = self.client.put(url, data=data, format='json')
        self.job.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_obj.update_job_length.apply.assert_called_with(kwargs={'job_id': self.job.id})
        self.assertEqual(self.job.name, job_name)
        self.assertIsNotNone(response.json()['estimated_testing_time'])

    @mock.patch('web_interface.api.job.serializers.tasks')
    def test_jobs_partial_update(self, mock_obj):
        url = reverse('api:jobs-detail', args=(self.job.id,))
        job_name = f'testJobPartiallyUpdated_{randint(0, 512)}'
        data = {
            'name': job_name
        }
        mock_obj.update_job_length.apply.side_effect = update_job_length_side_effect

        response = self.client.patch(url, data=data, format='json')
        self.job.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_obj.update_job_length.apply.assert_called_with(kwargs={'job_id': self.job.id})
        self.assertEqual(self.job.name, job_name)
        self.assertIsNotNone(response.json()['estimated_testing_time'])

    @mock.patch('web_interface.api.job.views.tasks')
    def test_jobs_destroy(self, mock_obj):
        mock_obj.abort_task.side_effect = lambda x: None

        url = reverse('api:jobs-detail', args=(self.job.id,))
        response = self.client.delete(url, format='json')

        abort_task_calls = (
            mock.call(self.task),
            mock.call(self.task_2)
        )
        mock_obj.abort_task.assert_has_calls(abort_task_calls, any_order=True)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Job.objects.all().count())

    # def test_start_jira_integration(self):
    #     url = reverse('api:jobs-start-jira-integration', args=(self.job.id,))
    #     response = self.client.post(url, format='json')
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #
    #     task = JiraTask.objects.filter(jira_integration=self.jira_integration_params, error_id='testErrId').first()
    #     self.assertIsNotNone(task)
    #     key = task.jira_task_key
    #     task.delete()
    #
    #     jira = JIRA(self.jira_integration_params.host,
    #                 basic_auth=(self.jira_integration_params.username, self.jira_integration_params.token))
    #     try:
    #         jira_issue = jira.issue(key)
    #     except JIRAError:
    #         jira.close()
    #         self.fail()
    #     subtasks_len = len(jira_issue.fields.subtasks)
    #     for sub_issue in jira_issue.fields.subtasks:
    #         sub_issue.delete()
    #     jira_issue.delete()
    #     jira.close()
    #     self.assertEqual(subtasks_len, 1)
