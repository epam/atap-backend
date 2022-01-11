from random import randint

from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.page.models import Page


class PageViewSetTestCase(CommonAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.page = Page.objects.create(name='testPage', url='testUrl', project=self.project)

    def tearDown(self) -> None:
        super().tearDown()
        self.page.delete()

    def test_pages_list(self):
        url = reverse('api:pages-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'][0]['name'], self.page.name)

    def test_pages_entire(self):
        url = reverse('api:pages-entire')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()[0]['name'], self.page.name)

    def test_pages_create(self):
        url = reverse('api:pages-list')
        page_name = f'testPageCreated_{randint(0, 512)}'
        data = {
            'name': page_name,
            'url': 'http://example.com',
            'project': self.project.id
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        page_id = response.json()['id']
        self.assertEqual(Page.objects.get(id=page_id).name, page_name)

    def test_pages_retrieve(self):
        url = reverse('api:pages-detail', args=(self.page.id,))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['name'], self.page.name)
        self.assertEqual(response.json()['url'], self.page.url)

    def test_pages_update(self):
        url = reverse('api:pages-detail', args=(self.page.id,))
        page_name = f'testPageUpdated_{randint(0, 512)}'
        data = {
            'name': page_name,
            'url': 'http://example.com',
            'project': self.project.id
        }

        response = self.client.put(url, data=data, format='json')
        self.page.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.page.name, page_name)

    def test_pages_partial_update(self):
        url = reverse('api:pages-detail', args=(self.page.id,))
        page_name = f'testPagePartiallyUpdated_{randint(0, 512)}'
        data = {
            'name': page_name
        }
        response = self.client.patch(url, data=data, format='json')
        self.page.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.page.name, page_name)

    def test_pages_destroy(self):
        url = reverse('api:pages-detail', args=(self.page.id,))
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Page.objects.all().count())
