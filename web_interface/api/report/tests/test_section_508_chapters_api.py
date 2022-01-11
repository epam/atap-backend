from random import randint

from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.framework_data.models import TestResults
from web_interface.apps.job.models import Job
from web_interface.apps.report.models import Section508Chapters, VpatReportParams


class Section508CriteriaViewSetTestCase(CommonAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.job = Job.objects.create(
            name='testJob', test_list=['test_fake_ok'], project=self.project, creator=self.super_user
        )
        self.test_results = TestResults.objects.create()
        self.vpat_report_params = VpatReportParams.objects.create(
            project=self.project, job=self.job,
            type='testType', standart='testStandart', product_type='tesProduct_type'
        )
        self.section_508_chapters = Section508Chapters.objects.create(
            name='test_name', chapter='test_chapter', note='test_note'
        )

    def tearDown(self) -> None:
        self.section_508_chapters.delete()
        self.test_results.delete()
        self.vpat_report_params.delete()
        self.job.delete()
        super().tearDown()

    def test_section_508_chapters_list(self):
        url = reverse('api:section-508-chapters-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'][0]['name'], self.section_508_chapters.name)
        self.assertEqual(response.json()['results'][0]['chapter'], self.section_508_chapters.chapter)

    def test_section_508_chapters_create(self):
        url = reverse('api:section-508-chapters-list')
        section_508_chapters_name = f'test_{randint(0, 512)}'
        data = {
            'name': section_508_chapters_name,
            'note': 'test_note',
            'chapter': 'test_chapter',
            'test_results': self.test_results.id,
            'report': self.vpat_report_params.id
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        section_508_chapters_id = response.json()['id']
        self.assertEqual(
            Section508Chapters.objects.get(id=section_508_chapters_id).name,
            section_508_chapters_name
        )

    def test_section_508_chapters_retrieve(self):
        url = reverse('api:section-508-chapters-detail', args=(self.section_508_chapters.id,))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['name'], self.section_508_chapters.name)
        self.assertEqual(response.json()['chapter'], self.section_508_chapters.chapter)

    def test_section_508_chapters_update(self):
        url = reverse('api:section-508-chapters-detail', args=(self.section_508_chapters.id,))
        section_508_chapters_name = f'test_{randint(0, 512)}'
        data = {
            'name': section_508_chapters_name,
            'note': 'test_note',
            'chapter': 'test_chapter',
            'test_results': self.test_results.id,
            'report': self.vpat_report_params.id
        }

        response = self.client.put(url, data=data, format='json')
        self.section_508_chapters.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.section_508_chapters.name, section_508_chapters_name)

    def test_section_508_chapters_partial_update(self):
        url = reverse('api:section-508-chapters-detail', args=(self.section_508_chapters.id,))
        section_508_chapters_name = f'test_{randint(0, 512)}'
        data = {
            'name': section_508_chapters_name,
        }
        response = self.client.patch(url, data=data, format='json')
        self.section_508_chapters.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.section_508_chapters.name, section_508_chapters_name)

    def test_section_508_chapters_destroy(self):
        url = reverse('api:section-508-chapters-detail', args=(self.section_508_chapters.id,))
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Section508Chapters.objects.all().count())
