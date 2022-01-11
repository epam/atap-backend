from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.framework_data.models import AvailableTestGroup


class AvailableTestGroupViewSetTestCase(CommonAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.available_test_group = AvailableTestGroup.objects.create(name='Major')

    def tearDown(self) -> None:
        self.available_test_group.delete()
        super().tearDown()

    def test_test_results_list(self):
        url = reverse('api:available-test-group-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()[0]['id'], self.available_test_group.id)
        self.assertEqual(response.json()[0]['name'], self.available_test_group.name)

    def test_test_results_retrieve(self):
        url = reverse('api:available-test-group-detail', args=(self.available_test_group.id,))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['id'], self.available_test_group.id)
        self.assertEqual(response.json()['name'], self.available_test_group.name)
