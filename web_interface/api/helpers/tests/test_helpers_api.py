from unittest import mock

from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.backend.url_checker import CheckUrlResponse


class UrlValidationAPIViewTestCase(CommonAPITestCase):
    @mock.patch("web_interface.api.helpers.views.url_checker")
    def test_get(self, mock_obj):
        url = reverse("api-url-validation")
        post_data = {"url": "https://www.google.com"}
        title = "Test Title"
        mock_obj.check_url.return_value = CheckUrlResponse(
            message="return_message", is_valid=True, status_code=200, title=title
        )

        response = self.client.post(url, data=post_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_obj.check_url.assert_called_with(post_data["url"])
        self.assertTrue(response.json()["is_valid"])
        self.assertEqual(response.json()["title"], title)


class AuthValidationAPIViewTestCase(CommonAPITestCase):
    def test_auth_page(self):
        url = reverse("api-auth-validation")
        post_data = {
            "url": "https://pypi.org/",
            "auth_type": "page",
            "auth_setting": {
                "activator": "https://pypi.org/account/login/",
                "login": "sephoratest",
                "password": "Xa35qXCExBUf",
            },
        }

        response = self.client.post(url, data=post_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["is_valid"])

    # def test_auth_modal(self):
    #     url = reverse("api-auth-validation")
    #     post_data = {
    #         "url": "https://juicebro.com/en/",
    #         "auth_type": "modal",
    #         "auth_setting": {
    #             "activator": "a[href='https://juicebro.com/en/my-account/']",
    #             "login": "victor.hugo.77@list.ru",
    #             "password": "Checkertest123",
    #         },
    #     }

    #     response = self.client.post(url, data=post_data, format="json")
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertTrue(response.json()["is_valid"])

    # def test_auth_alert(self):
    # url = reverse("api-auth-validation")
    # # * bad test example, it authenticates through direct link
    # post_data = {
    #     "url": "https://the-internet.herokuapp.com/basic_auth/",
    #     "auth_type": "alert",
    #     "auth_setting": {"login": "admin", "password": "admin"},
    # }

    # response = self.client.post(url, data=post_data, format="json")
    # self.assertEqual(response.status_code, status.HTTP_200_OK)
    # self.assertTrue(response.json()["is_valid"])


class FrameworkMetadataAPIViewTestCase(CommonAPITestCase):
    def test_get(self):
        url = reverse("api-framework-metadata")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(type(response.json()["sr_versions"]), list)


class ApplicationInfoAPIViewTestCase(CommonAPITestCase):
    @override_settings(APPLICATION_BUILD_REVISION="12347")
    def test_get(self):
        url = reverse("api-application-info")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["build"], "12347")


class MataDataForIssueAPIViewTestCase(CommonAPITestCase):
    @mock.patch("web_interface.api.helpers.views.xlsdata")
    def test_get(self, mock_obj):
        err_id = "test_err_id"
        url = reverse("api-metadata-for-issue", args=(err_id,))
        mock_obj.get_data_for_issue.side_effect = lambda x: {"err_id": x}

        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_obj.get_data_for_issue.assert_called_with(err_id)
        self.assertEqual(response.json()["err_id"], err_id)
