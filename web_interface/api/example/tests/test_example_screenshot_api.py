import base64
import io

from PIL import Image
from django.urls import reverse
from rest_framework import status

from web_interface.api.test_base import CommonAPITestCase
from web_interface.apps.issue.models import Example, ExampleScreenshot
from web_interface.apps.job.models import Job
from web_interface.apps.report.models import Issue
from web_interface.apps.task.models import Task
from web_interface.apps.framework_data.models import TestResults


class ExampleScreenshotViewSetTestCase(CommonAPITestCase):

    @staticmethod
    def generate_screenshot_data():
        file = io.BytesIO()
        image = Image.new('RGBA', size=(100, 100), color=(155, 0, 0))
        image.save(file, 'png')
        file.name = 'test_screenshot_file.png'
        file.seek(0)
        data = file.read()
        file.close()
        return base64.b64encode(data).decode('utf-8')

    def setUp(self) -> None:
        super().setUp()

        self.test_results = TestResults.objects.create()
        self.job = Job.objects.create(
            name='testJob', test_list=['test_fake_ok'], project=self.project, creator=self.super_user
        )
        self.task = Task.objects.create(
            target_job=self.job, status=Task.RUNNING, message='testMessage', test_results=self.test_results
        )
        self.issue = Issue.objects.create(
            err_id='testErrId', test_results=self.test_results,
            wcag='testWCAG', is_best_practice=True
        )
        self.example = Example.objects.create(
            err_id='testErrId', test_results=self.test_results, issue=self.issue,
            code_snippet='testCodeSnippet', problematic_element_selector='testProblematicElementSelector'
        )
        self.example_screenshot = ExampleScreenshot.objects.create(example=self.example)
        data = self.generate_screenshot_data()
        file = io.BytesIO()
        file.write(data.encode(encoding='utf-8'))
        file.seek(0)
        self.example_screenshot.screenshot.save('test_screenshot_file', file)
        file.close()

    def tearDown(self) -> None:
        self.example_screenshot.delete()
        self.example.delete()
        self.issue.delete()
        self.task.delete()
        self.job.delete()
        self.test_results.delete()
        super().tearDown()

    def test_example_screenshot_list(self):
        url = reverse('api:example-screenshot-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'][0]['id'], self.example_screenshot.id)
        self.assertEqual(response.json()['results'][0]['example'], self.example.id)

    def test_example_screenshot_retrieve(self):
        url = reverse('api:example-screenshot-detail', args=(self.example_screenshot.id,))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['id'], self.example_screenshot.id)
        self.assertEqual(response.json()['example'], self.example.id)
        
    def test_example_screenshot_create(self):
        url = reverse('api:example-screenshot-list')
        data = self.generate_screenshot_data()
        data = {
            'example': self.example.id,
            'image': data
        }
        response = self.client.post(url, data=data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        example_screenshot = ExampleScreenshot.objects.get(id=response.json()['id'])
        self.assertEqual(example_screenshot.example_id, self.example.id)
        self.assertIsNotNone(example_screenshot.screenshot)

    def test_example_screenshot_destroy(self):
        url = reverse('api:example-screenshot-detail', args=(self.example_screenshot.id,))
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ExampleScreenshot.objects.all().count())
