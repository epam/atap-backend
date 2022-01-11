from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.job.models import Job
from web_interface.apps.task.models import Task


# class TaskReportsViewSetTestCase(CommonAPITestCase):
#     def setUp(self) -> None:
#         super().setUp()
#
#         self.job = Job.objects.create(
#             name='testJob', test_list=['test_fake_ok'], project=self.project, creator=self.super_user
#         )
#         self.task = Task.objects.create(target_job=self.job, status=Task.RUNNING, message='testMessage')
#
#     def tearDown(self) -> None:
#         self.task.delete()
#         self.job.delete()
#         super().tearDown()
#
#     def test_task_reports_list(self):
#         url = reverse('api:task-reports-list')
#         response = self.client.get(url, format='json')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.json()['results'][0]['status'], self.task.status)
#         self.assertEqual(response.json()['results'][0]['message'], self.task.message)
#
#     def test_task_reports_retrieve(self):
#         url = reverse('api:task-reports-detail', args=(self.task.id,))
#         response = self.client.get(url, format='json')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.json()['status'], self.task.status)
#         self.assertEqual(response.json()['message'], self.task.message)
