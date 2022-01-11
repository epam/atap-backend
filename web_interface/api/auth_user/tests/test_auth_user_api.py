from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.auth_user.models import DemoPermissions
from web_interface.apps.framework_data.models import AvailableTest


class AuthUserAPIViewTestCase(CommonAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.test_axe = AvailableTest.objects.create(
            name='area-alt',
            human_name='WCAG 1.1.1 - Ensures <area> elements of image maps have alternate text (1.1.1, 2.4.4, 4.1.2)'
        )
        self.test_custom = AvailableTest.objects.create(
            name='test_image_alt',
            human_name='WCAG 1.1.1 - Ensures that all images have meaningful text alternatives'
        )
        self.demo_permissions = DemoPermissions.objects.create(
            user=self.super_user, is_reports_readonly=False, available_tests=[self.test_custom.name]
        )

    def tearDown(self) -> None:
        super().tearDown()
        self.demo_permissions.delete()
        self.test_axe.delete()
        self.test_custom.delete()

    def test_auth_user_retrieve(self):
        url = reverse('api-auth-user')
        response = self.client.get(url, format='json')
        response_json = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response_json['id'], self.super_user.id)
        self.assertEqual(response_json['demo_permissions']['projects_quota'], self.demo_permissions.projects_quota)
        self.assertEqual(response_json['demo_permissions']['pages_quota'], self.demo_permissions.pages_quota)
        self.assertEqual(response_json['demo_permissions']['jobs_quota'], self.demo_permissions.jobs_quota)
        self.assertEqual(response_json['demo_permissions']['is_reports_readonly'],
                         self.demo_permissions.is_reports_readonly)

        self.assertEqual(sorted(response_json['demo_permissions']['available_tests']),
                         sorted([self.test_axe.name, self.test_custom.name]))
