from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.framework_data.models import AvailableTest, AvailableTestGroup


class AvailableTestViewSetTestCase(CommonAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.available_test = AvailableTest.objects.create(name='available_test_name',
                                                           human_name='available_test_human_name')
        self.groups_names = ('Fast Run', 'Major')
        for group_name in self.groups_names:
            available_test_group, _ = AvailableTestGroup.objects.get_or_create(name=group_name)
            self.available_test.groups.add(available_test_group)

    def tearDown(self) -> None:
        self.available_test.groups.all().delete()
        self.available_test.delete()
        super().tearDown()

    def test_test_results_list(self):
        url = reverse('api:available-test-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()[0]['id'], self.available_test.id)
        self.assertEqual(sorted(response.json()[0]['groups_names']), sorted(self.groups_names))

    def test_test_results_retrieve(self):
        url = reverse('api:available-test-detail', args=(self.available_test.id,))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['id'], self.available_test.id)
        self.assertEqual(sorted(response.json()['groups_names']), sorted(self.groups_names))
