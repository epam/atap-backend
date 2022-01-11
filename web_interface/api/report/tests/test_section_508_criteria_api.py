from random import randint

from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.report.models import Section508Criteria, Section508Chapters


class Section508CriteriaViewSetTestCase(CommonAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.section_508_chapters = Section508Chapters.objects.create(
            name='test_name', chapter='test_chapter', note='test_note'
        )
        self.section_508_criteria = Section508Criteria.objects.create(
            criteria='test_criteria', level='test_level', remark='test_remark'
        )

    def tearDown(self) -> None:
        self.section_508_chapters.delete()
        self.section_508_criteria.delete()
        super().tearDown()

    def test_section_508_criteria_list(self):
        url = reverse('api:section-508-criteria-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'][0]['criteria'], self.section_508_criteria.criteria)
        self.assertEqual(response.json()['results'][0]['level'], self.section_508_criteria.level)

    def test_section_508_criteria_create(self):
        url = reverse('api:section-508-criteria-list')
        section_508_criteria_criteria = f'test_{randint(0, 512)}'
        data = {
            'criteria': section_508_criteria_criteria,
            'remark': 'test_remark',
            'level': 'test_level',
            'product_type': None,
            'chapter': self.section_508_chapters.id
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        section_508_criteria_id = response.json()['id']
        self.assertEqual(
            Section508Criteria.objects.get(id=section_508_criteria_id).criteria,
            section_508_criteria_criteria
        )

    def test_section_508_criteria_retrieve(self):
        url = reverse('api:section-508-criteria-detail', args=(self.section_508_criteria.id,))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['criteria'], self.section_508_criteria.criteria)
        self.assertEqual(response.json()['level'], self.section_508_criteria.level)

    def test_section_508_criteria_update(self):
        url = reverse('api:section-508-criteria-detail', args=(self.section_508_criteria.id,))
        section_508_criteria_criteria = f'test_{randint(0, 512)}'
        data = {
            'criteria': section_508_criteria_criteria,
            'remark': 'test_remark',
            'level': 'test_level',
            'product_type': None,
            'chapter': self.section_508_chapters.id
        }

        response = self.client.put(url, data=data, format='json')
        self.section_508_criteria.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.section_508_criteria.criteria, section_508_criteria_criteria)

    def test_section_508_criteria_partial_update(self):
        url = reverse('api:section-508-criteria-detail', args=(self.section_508_criteria.id,))
        section_508_criteria_criteria = f'test_{randint(0, 512)}'
        data = {
            'criteria': section_508_criteria_criteria,
        }
        response = self.client.patch(url, data=data, format='json')
        self.section_508_criteria.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.section_508_criteria.criteria, section_508_criteria_criteria)

    def test_section_508_criteria_destroy(self):
        url = reverse('api:section-508-criteria-detail', args=(self.section_508_criteria.id,))
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Section508Criteria.objects.all().count())
