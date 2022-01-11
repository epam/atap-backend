from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from web_interface.apps.api_key.models import CheckerAPIKey
from web_interface.apps.project.models import Project, ProjectRole

User = get_user_model()


class CommonAPITestCase(APITestCase):
    def setUp(self) -> None:
        self.super_user = User.objects.create_superuser(
            username='testSuperUser', email='test@example.com', password='test_password'
        )
        self.project = Project.objects.create(name='testProject', comment='This is a test project')
        role = ProjectRole.objects.create(name='Owner')
        self.project.users.add(self.super_user, through_defaults={'role': role})
        self.client.force_authenticate(user=self.super_user)

    def tearDown(self) -> None:
        self.project.delete()
        self.super_user.delete()


class SeparatedClientsAPITestCase(CommonAPITestCase):
    def prepare_api_key_client(self) -> None:
        self.api_key_obj, self.api_key = CheckerAPIKey.objects.create_key(
            project=self.project, user=self.super_user, name=self.project.name
        )
        self.api_key_client = self.client_class()
        self.api_key_client.credentials(HTTP_AUTHORIZATION=f'Api-Key {self.api_key}')

    def setUp(self) -> None:
        super().setUp()
        self.prepare_api_key_client()

    def tearDown(self) -> None:
        self.api_key_obj.delete()
        super().tearDown()
