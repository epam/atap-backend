from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase

User = get_user_model()


class ChangePasswordAPIViewTestCase(CommonAPITestCase):

    def test_change_password_update(self):
        url = reverse('api-change-password')
        data = {
            'old_password': 'test_password',
            'new_password': 'new_test_password',
            'new_password_confirmation': 'new_test_password'
        }

        response = self.client.put(url, data=data, format='json')
        response_json = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response_json['user_id'], self.super_user.id)
        self.assertIsNotNone(response_json['token'])
