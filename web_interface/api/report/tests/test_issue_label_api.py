from random import randint

from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.framework_data.models import TestResults
from web_interface.apps.report.models import IssueLabel


class IssueLabelViewSetTestCase(CommonAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.test_results = TestResults.objects.create()
        self.issue_label = IssueLabel.objects.create(name='test_name', test_results=self.test_results)

    def tearDown(self) -> None:
        self.issue_label.delete()
        self.test_results.delete()
        super().tearDown()

    def test_issue_label_list(self):
        url = reverse('api:issue-label-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'][0]['id'], self.issue_label.id)
        self.assertEqual(response.json()['results'][0]['name'], self.issue_label.name)
        self.assertEqual(response.json()['results'][0]['test_results'], self.test_results.id)

    def test_issue_label_create(self):
        url = reverse('api:issue-label-list')
        issue_label_name = f'test_{randint(0, 512)}'
        data = {
            'name': issue_label_name,
            'test_results': self.test_results.id
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        issue_label_id = response.json()['id']
        self.assertEqual(
            IssueLabel.objects.get(id=issue_label_id).name,
            issue_label_name
        )

    def test_issue_label_retrieve(self):
        url = reverse('api:issue-label-detail', args=(self.issue_label.id,))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['id'], self.issue_label.id)
        self.assertEqual(response.json()['name'], self.issue_label.name)
        self.assertEqual(response.json()['test_results'], self.test_results.id)

    def test_issue_label_update(self):
        url = reverse('api:issue-label-detail', args=(self.issue_label.id,))
        issue_label_name = f'test_{randint(0, 512)}'
        data = {
            'name': issue_label_name,
            'test_results': self.test_results.id
        }

        response = self.client.put(url, data=data, format='json')
        self.issue_label.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.issue_label.name, issue_label_name)

    def test_issue_label_partial_update(self):
        url = reverse('api:issue-label-detail', args=(self.issue_label.id,))
        issue_label_name = f'test_{randint(0, 512)}'
        data = {
            'name': issue_label_name,
        }
        response = self.client.patch(url, data=data, format='json')
        self.issue_label.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.issue_label.name, issue_label_name)

    def test_issue_label_destroy(self):
        url = reverse('api:issue-label-detail', args=(self.issue_label.id,))
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(IssueLabel.objects.all().count())
