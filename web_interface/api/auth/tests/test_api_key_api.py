from random import randint

from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import SeparatedClientsAPITestCase
from web_interface.apps.api_key.models import CheckerAPIKey


class CheckerAPIKeyViewSetTestCase(SeparatedClientsAPITestCase):

    def test_api_key_list(self):
        url = reverse('api:api-key-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'][0]['user'], self.super_user.id)

    def test_api_key_create(self):
        url = reverse('api:api-key-list')

        api_key_name = f'api_key_nameCreated_{randint(0, 512)}'
        data = {
            'name': api_key_name,
            'project': self.project.id
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('key', response.json())

    def test_api_key_delete(self):
        url = reverse('api:api-key-delete')
        data = {'token_id': self.api_key_obj.id}
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CheckerAPIKey.objects.all().count())
