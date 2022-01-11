from unittest import mock

from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.framework_data.models import TestResults, Test
from web_interface.apps.issue.models import Example
from web_interface.apps.job.models import Job
from web_interface.apps.page.models import Page
from web_interface.apps.report.models import ConformanceLevel, Issue
from web_interface.apps.task.models import Task


class AuditReportViewSetTestCase(CommonAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.job = Job.objects.create(
            name='testJob', test_list=['test_fake_ok'], project=self.project, creator=self.super_user
        )
        self.test_results = TestResults.objects.create()
        self.job = Job.objects.create(
            name='testJob', test_list=['test_fake_ok'], project=self.project, creator=self.super_user
        )
        self.task = Task.objects.create(
            target_job=self.job, status=Task.RUNNING, message='testMessage', test_results=self.test_results
        )
        self.issue = Issue.objects.create(
            name='testName', err_id='testErrId', test_results=self.test_results,
            wcag='testWCAG', is_best_practice=True, priority='Major'
        )
        self.page = Page.objects.create(name='testPage', url='testUrl', project=self.project)
        self.example = Example.objects.create(
            err_id='testErrId', test_results=self.test_results, issue=self.issue,
            code_snippet='testCodeSnippet', problematic_element_selector='testProblematicElementSelector'
        )
        self.example.pages.add(self.page)
        self.example_warn = Example.objects.create(
            err_id='testErrId', test_results=self.test_results, issue=None, severity='WARN',
            code_snippet='testCodeSnippet', problematic_element_selector='testProblematicElementSelector'
        )
        self.test = Test.objects.create(
            name='testTest', status=Test.ERROR, support_status='testSupport_status',
            problematic_pages='tastProblematic_pages', test_results=self.test_results
        )
        self.conformance_level = ConformanceLevel.objects.create(
            WCAG='testWCAG', test_results=self.test_results, level='Support'
        )
        self.conformance_level.issues.add(self.issue)

    def tearDown(self) -> None:
        self.conformance_level.delete()
        self.page.delete()
        self.example.delete()
        self.issue.delete()
        self.task.delete()
        self.job.delete()
        self.test.delete()
        self.example_warn.delete()
        self.test_results.delete()
        super().tearDown()

    @mock.patch('web_interface.api.report.serializers.get_available_problem_types')
    def test_audit_report_list(self, mock_obj):
        url = reverse('api:audit-reports-list')
        mock_obj.return_value = (), ()
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_obj.assert_called()
        response_json = response.json()
        self.assertEqual(response_json['results'][0]['id'], self.task.id)
        self.assertIn('issues', response_json['results'][0])
        self.assertIn('wcag_checklist', response_json['results'][0])
        self.assertEqual(response_json['results'][0]['available_problem_types'], {'wcag': [], 'bp': []})

    @mock.patch('web_interface.api.report.serializers.get_available_problem_types')
    def test_audit_report_retrieve(self, mock_obj):
        url = reverse('api:audit-reports-detail', args=(self.task.id,))
        mock_obj.return_value = (), ()
        response = self.client.get(url + '?priority=Major,Fake', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_obj.assert_called()
        response_json = response.json()
        self.assertEqual(response_json['id'], self.task.id)
        self.assertIn('issues', response_json)
        self.assertIn('wcag_checklist', response_json)
        self.assertEqual(response_json['available_problem_types'], {'wcag': [], 'bp': []})

    def test_audit_report_pages(self):
        url = reverse('api:audit-reports-pages', args=(self.task.id,))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = response.json()
        self.assertEqual(response_json['results'][0]['id'], self.page.id)

    def test_audit_report_download_as_xlsx(self):
        url = reverse('api:audit-reports-download-as-xlsx', args=(self.task.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.has_header('Access-Control-Expose-Headers'))
        self.assertEqual(response._headers['content-type'][1],
                         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

