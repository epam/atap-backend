from random import randint
from unittest import mock

from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.project.models import Project, ProjectPermission, ProjectRole


class ProjectViewSetTestCase(CommonAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        project_role, _ = ProjectRole.objects.get_or_create(name='Admin')
        self.test_project_permission = ProjectPermission.objects.create(
            project=self.project, user=self.super_user, role=project_role
        )

    def tearDown(self) -> None:
        self.test_project_permission.delete()
        super().tearDown()

    def test_projects_list(self):
        url = reverse('api:projects-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'][0]['name'], self.project.name)

    def test_projects_simplified(self):
        url = reverse('api:projects-simplified')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()[0]['id'], self.project.id)
        self.assertEqual(response.json()[0]['name'], self.project.name)

    def test_projects_create(self):
        # print("*" * 60)
        # print("test_projects_create of ProjectViewSetTestCase")
        # print("*" * 60)
        url = reverse('api:projects-list')
        project_name = f'testProjectCreated_{randint(0, 512)}'
        project_roles = [f'Admin_{randint(0, 512)}', f'Viewer_{randint(0, 512)}']
        data = {
            'name': project_name,
            'url': 'http://example.com',
            'comment': 'testComment',
            'contact': 'testContact',
            'company': 'testCompany',
            'page_after_login': True,
            'options': Project.DEFAULT_AUTH_OPTIONS,
            'users': [
                {
                    'user': self.super_user.id,
                    'role': role
                }
                for role in project_roles
            ]
        }

        # print("url", url)
        # print("project_name", project_name)
        # print("project_roles", project_roles)
        # print("data", data)

        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        project_id = response.json()['id']
        created_project = Project.objects.get(id=project_id)
        created_project_roles = ProjectRole.objects.filter(
            project_permissions__project=created_project, project_permissions__user=self.super_user
        ).values_list('name', flat=True)
        self.assertTrue(created_project.page_after_login)
        self.assertEqual(created_project.name, project_name)
        self.assertEqual(sorted(created_project_roles), sorted(project_roles + ['Creator']))
        # print("OK...test_projects_create...OK")


    def test_projects_retrieve(self):
        url = reverse('api:projects-detail', args=(self.project.id,))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['name'], self.project.name)
        self.assertEqual(response.json()['has_activities'], False)

    def test_projects_update(self):
        url = reverse('api:projects-detail', args=(self.project.id,))
        project_name = f'testProjectUpdated_{randint(0, 512)}'
        project_roles = [f'Admin_U_{randint(0, 512)}', f'Viewer_U_{randint(0, 512)}']
        data = {
            'name': project_name,
            'url': 'http://example.com',
            'comment': 'testComment',
            'contact': 'testContact',
            'company': 'testCompany',
            'options': Project.DEFAULT_AUTH_OPTIONS,
            'page_after_login': True,
            'users': [
                {
                    'user': self.super_user.id,
                    'role': role
                }
                for role in project_roles
            ]
        }

        response = self.client.put(url, data=data, format='json')
        self.project.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_project_roles = ProjectRole.objects.filter(
            project_permissions__project=self.project, project_permissions__user=self.super_user
        ).values_list('name', flat=True)
        self.assertTrue(self.project.page_after_login)
        self.assertEqual(self.project.name, project_name)
        self.assertEqual(sorted(updated_project_roles), sorted(project_roles + ['Creator']))

    def test_projects_partial_update(self):
        url = reverse('api:projects-detail', args=(self.project.id,))
        project_name = f'testProjectPartiallyUpdated_{randint(0, 512)}'
        data = {
            'name': project_name
        }
        response = self.client.patch(url, data=data, format='json')
        self.project.refresh_from_db()
        updated_project_roles = ProjectRole.objects.filter(
            project_permissions__project=self.project, project_permissions__user=self.super_user
        ).values_list('name', flat=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.project.name, project_name)
        self.assertEqual(sorted(updated_project_roles), sorted(['Admin', 'Owner']))

    def test_projects_destroy(self):
        url = reverse('api:projects-detail', args=(self.project.id,))
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Project.objects.all().count())

    @mock.patch('web_interface.apps.task.tasks')
    def test_projects_is_sitemap_running(self, mock_obj):
        url = reverse('api:projects-is-sitemap-running', args=(self.project.id,))

        returned_value = True
        mock_obj.is_sitemap_running.return_value = returned_value

        response = self.client.get(url, format='json')
        mock_obj.is_sitemap_running.assert_called_with(self.project.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['is_running'], returned_value)

    @mock.patch('web_interface.apps.task.tasks')
    def test_projects_generate_sitemap(self, mock_obj):
        url = reverse('api:projects-generate-sitemap', args=(self.project.id,))
        mock_obj.generate_sitemap.side_effect = lambda *args, **kwargs: None

        response = self.client.post(url, format='json')
        mock_obj.generate_sitemap.assert_called_with(self.project.id, 1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['status'], 'Sitemap generation started')

    def test_projects_companies(self):
        url = reverse('api:projects-companies')

        # preparation stage
        company = f'testCompany_{randint(0, 512)}'
        self.project.company = company
        self.project.save()

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['companies'], [company])
