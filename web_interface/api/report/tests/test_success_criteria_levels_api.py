from random import randint

from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.report.models import SuccessCriteriaLevel


class SuccessCriteriaLevelViewSetTestCase(CommonAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.success_criteria_level = SuccessCriteriaLevel.objects.create(
            criteria='test_criteria', product_type='test_product_type', level='test_level'
        )

    def tearDown(self) -> None:
        self.success_criteria_level.delete()
        super().tearDown()

    def test_success_criteria_levels_list(self):
        url = reverse('api:success-criteria-levels-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'][0]['criteria'], self.success_criteria_level.criteria)
        self.assertEqual(response.json()['results'][0]['level'], self.success_criteria_level.level)

    def test_success_criteria_levels_create(self):
        url = reverse('api:success-criteria-levels-list')
        success_criteria_level_criteria = f'test_{randint(0, 512)}'
        data = {
            'criteria': success_criteria_level_criteria,
            'product_type': 'test_product_type',
            'level': 'test_level'
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        success_criteria_level_id = response.json()['id']
        self.assertEqual(
            SuccessCriteriaLevel.objects.get(id=success_criteria_level_id).criteria,
            success_criteria_level_criteria
        )

    def test_success_criteria_levels_retrieve(self):
        url = reverse('api:success-criteria-levels-detail', args=(self.success_criteria_level.id,))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['criteria'], self.success_criteria_level.criteria)
        self.assertEqual(response.json()['level'], self.success_criteria_level.level)

    def test_success_criteria_levels_update(self):
        url = reverse('api:success-criteria-levels-detail', args=(self.success_criteria_level.id,))
        success_criteria_level_criteria = f'test_{randint(0, 512)}'
        data = {
            'criteria': success_criteria_level_criteria,
            'product_type': 'test_product_type',
            'level': 'test_level'
        }

        response = self.client.put(url, data=data, format='json')
        self.success_criteria_level.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.success_criteria_level.criteria, success_criteria_level_criteria)

    def test_success_criteria_levels_partial_update(self):
        url = reverse('api:success-criteria-levels-detail', args=(self.success_criteria_level.id,))
        success_criteria_level_criteria = f'test_{randint(0, 512)}'
        data = {
            'criteria': success_criteria_level_criteria,
        }
        response = self.client.patch(url, data=data, format='json')
        self.success_criteria_level.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.success_criteria_level.criteria, success_criteria_level_criteria)

    def test_success_criteria_levels_destroy(self):
        url = reverse('api:success-criteria-levels-detail', args=(self.success_criteria_level.id,))
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SuccessCriteriaLevel.objects.all().count())
