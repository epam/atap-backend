from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.job.models import Job
from web_interface.apps.task.models import Task
from web_interface.apps.framework_data.models import TestResults


class TestResultsViewSetTestCase(CommonAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_results = TestResults.objects.create()
        self.job = Job.objects.create(
            name='testJob', test_list=['test_fake_ok'], project=self.project, creator=self.super_user
        )
        self.task = Task.objects.create(
            target_job=self.job, status=Task.RUNNING, message='testMessage', test_results=self.test_results
        )

    def tearDown(self) -> None:
        self.task.delete()
        self.job.delete()
        self.test_results.delete()
        super().tearDown()

    def test_test_results_list(self):
        url = reverse('api:test-results-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'][0]['id'], self.test_results.id)

    def test_test_results_retrieve(self):
        url = reverse('api:test-results-detail', args=(self.test_results.id,))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['id'], self.test_results.id)
