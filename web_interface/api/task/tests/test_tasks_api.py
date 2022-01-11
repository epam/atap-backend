import io
from unittest import mock

from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.framework_data.models import TestResults, AvailableTest
from web_interface.apps.job.models import Job
from web_interface.apps.report.models import VpatReportParams, ConformanceLevel
from web_interface.apps.task.models import Task


class TaskViewSetTestCase(CommonAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.job = Job.objects.create(
            name='testJob', test_list=['test_fake_ok'], project=self.project, creator=self.super_user
        )
        self.test_results = TestResults.objects.create()
        self.task = Task.objects.create(
            target_job=self.job, status=Task.RUNNING, test_results=self.test_results, message='testMessage'
        )
        self.conformance_level = ConformanceLevel.objects.create(
            WCAG='testWCAG', test_results=self.test_results, level='Support'
        )

    def tearDown(self) -> None:
        self.task.delete()
        self.conformance_level.delete()
        self.test_results.delete()
        self.job.delete()
        super().tearDown()

    def test_tasks_list(self):
        url = reverse('api:tasks-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'][0]['status'], self.task.status)
        self.assertEqual(response.json()['results'][0]['message'], self.task.message)

    def test_tasks_retrieve(self):
        url = reverse('api:tasks-detail', args=(self.task.id,))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['status'], self.task.status)
        self.assertEqual(response.json()['message'], self.task.message)

    @mock.patch('web_interface.api.task.views.tasks')
    def test_tasks_abort_test_for_task(self, mock_obj):
        url = reverse('api:tasks-abort-test-for-task', args=(self.task.id,))
        mock_obj.cancel_test_for_task.side_effect = lambda *args, **kwargs: None
        available_test = AvailableTest.objects.create(name='test_name', human_name='test_human_name')
        data = {
            'test_name': available_test.name
        }
        response = self.client.post(url, data=data, format='json')
        mock_obj.cancel_test_for_task.assert_called_with(task_id=self.task.id, test_name=available_test.name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['status'], 'Test for Task Aborted')
        available_test.delete()

    @mock.patch('web_interface.api.task.views.tasks')
    def test_tasks_abort_task(self, mock_obj):
        url = reverse('api:tasks-abort-task', args=(self.task.id,))
        mock_obj.abort_task.side_effect = lambda x: None

        response = self.client.post(url, format='json')
        mock_obj.abort_task.assert_called_with(self.task)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['status'], 'Task Aborted')

    @mock.patch('web_interface.api.task.views.tasks')
    def test_tasks_get_status(self, mock_obj):
        test_results = TestResults.objects.create()
        queued_task = Task.objects.create(
            target_job=self.job, status=Task.QUEUED, test_results=test_results, message='testMessageQUEUED'
        )
        url = reverse('api:tasks-get-status')
        mock_obj.verify_tasks_running.side_effect = lambda *args, **kwargs: None
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.json()['running_tasks'][0]['task_id'], self.task.id)
        self.assertEqual(response.json()['queue_data'][0]['task_id'], queued_task.id)
        self.assertEqual(response.json()['all_queued_count'], 1)
        queued_task.delete()
        test_results.delete()

    @mock.patch('web_interface.api.task.views.update_conformance_level')
    @mock.patch('web_interface.api.task.views.update_success_criteria_level')
    @mock.patch('web_interface.api.task.views.update_level_for_section_chapter')
    def test_tasks_recalculate_wcag(self,
                                    update_level_for_section_chapter_mock_obj,
                                    update_success_criteria_level_mock_obj,
                                    update_conformance_level_mock_obj):
        url = reverse('api:tasks-recalculate-wcag', args=(self.task.id,))
        update_conformance_level_mock_obj.return_value = None
        update_success_criteria_level_mock_obj.return_value = None
        update_level_for_section_chapter_mock_obj.return_value = None

        response = self.client.post(url, format='json')
        update_conformance_level_mock_obj.assert_called_with(self.task.test_results)
        update_success_criteria_level_mock_obj.assert_called_with(self.task.test_results)
        update_level_for_section_chapter_calls = (
            mock.call(self.task.test_results, section='508', chapter='3'),
            mock.call(self.task.test_results, section='EN', chapter='4')
        )
        update_level_for_section_chapter_mock_obj.assert_has_calls(
            update_level_for_section_chapter_calls, any_order=True
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()[0]['id'], self.conformance_level.id)

    # @mock.patch('web_interface.api.task.views.report_generator')
    # def test_task_download_audit_report(self, mock_obj):
    #     url = reverse('api:tasks-download-audit-report', args=(self.task.id,))
    #     mock_obj.generate_report.return_value = io.BytesIO(b'test report data')
    #
    #     response = self.client.get(url, format='json')
    #     mock_obj.generate_report.assert_called_with(self.task, self.super_user)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(response.json()['status'], 'Report Generated')
    #     self.assertIn('report', response.json())
    #
    # @mock.patch('web_interface.api.task.views.report_generator')
    # def test_task_download_audit_report__method_file(self, mock_obj):
    #     url = reverse('api:tasks-download-audit-report', args=(self.task.id,))
    #     mock_obj.generate_report.return_value = io.BytesIO(b'test report data')
    #
    #     response = self.client.get(url, format='json')
    #     mock_obj.generate_report.assert_called_with(self.task, self.super_user)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(response.json()['status'], 'Report Generated')
    #     self.assertIn('filename', response.json())
    #     self.assertIn('report', response.json())
    #
    #     response_file = self.client.get(f'{url}?method=file', format='json')
    #     self.assertEqual(response_file.status_code, status.HTTP_200_OK)

    @mock.patch('framework.report.vpat_docx_report.VpatReport')
    def test_task_download_report(self, mock_obj):
        url = reverse('api:tasks-download-vpat-report', args=(self.task.id,), )

        mock_obj.create.side_effect = lambda filename: None
        vpat_report_params = VpatReportParams.objects.create(
            project=self.project,
            job=self.job,
            type='type',
            standart='standart',
            product_type='product_type'
        )

        response = self.client.get(f'{url}?vpat_report_id={vpat_report_params.id}', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['status'], 'Report Generated')
        self.assertIn('filename', response.json())
        self.assertIn('report', response.json())

        response_file = self.client.get(f'{url}?vpat_report_id={vpat_report_params.id}&method=file', format='json')
        self.assertEqual(response_file.status_code, status.HTTP_200_OK)
