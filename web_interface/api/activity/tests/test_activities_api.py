from random import randint

from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.activity.models import Activity
from web_interface.apps.page.models import Page


class ActivityViewSetTestCase(CommonAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.page = Page.objects.create(name='testPage', url='testUrl', project=self.project)
        self.activity = Activity.objects.create(name='testActivity', page=self.page)

    def tearDown(self) -> None:
        self.page.delete()
        self.activity.delete()
        super().tearDown()

    def test_activities_list(self):
        url = reverse('api:activities-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'][0]['name'], self.activity.name)

    def test_activities_create(self):
        url = reverse('api:activities-list')

        activity_name = f'testActivityCreated_{randint(0, 512)}'
        data = {
            'name': activity_name,
            'page': self.page.id,
            "click_sequence": "#test"
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        activity_id = response.json()['id']
        self.assertEqual(Activity.objects.get(id=activity_id).name, activity_name)

    def test_activities_retrieve(self):
        url = reverse('api:activities-detail', args=(self.activity.id,))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['name'], self.activity.name)

    def test_activities_update(self):
        url = reverse('api:activities-detail', args=(self.activity.id,))

        activity_name = f'testActivityUpdated_{randint(0, 512)}'
        data = {
            'name': activity_name,
            'page': self.page.id,
            "click_sequence": "#test"
        }

        response = self.client.put(url, data=data, format='json')
        self.activity.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.activity.name, activity_name)

    def test_activities_partial_update(self):
        url = reverse('api:activities-detail', args=(self.activity.id,))
        activity_name = f'testActivityPartiallyUpdated_{randint(0, 512)}'
        data = {
            'name': activity_name
        }
        response = self.client.patch(url, data=data, format='json')
        self.activity.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.activity.name, activity_name)

    def test_activities_destroy(self):
        url = reverse('api:activities-detail', args=(self.activity.id,))
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Activity.objects.all().count())
