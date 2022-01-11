from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.job.models import Job
from web_interface.apps.report.models import VpatReportParams
from web_interface.apps.task.models import Task


class VPATReportViewSetTestCase(CommonAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.job = Job.objects.create(
            name='testJob', test_list=['test_fake_ok'], project=self.project, creator=self.super_user
        )
        self.task = Task.objects.create(target_job=self.job, status=Task.SUCCESS, message='testMessage')
        self.vpat_report_params = VpatReportParams.objects.create(
            project=self.project, job=self.job,
            type='testType', standart='testStandart', product_type='tesProduct_type'
        )

    def tearDown(self) -> None:
        self.vpat_report_params.delete()
        self.task.delete()
        self.job.delete()
        super().tearDown()

    def test_vpat_report_retrieve(self):
        url = reverse('api-vpat-report-detail', args=(self.task.id, self.vpat_report_params.id))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = response.json()
        self.assertEqual(response_json['id'], self.vpat_report_params.id)
        self.assertIn('wcag', response_json)
        self.assertIn('chapters_508', response_json)
        self.assertIn('chapters_EN', response_json)
