from django.db import models

from framework import xlsdata


class Example(models.Model):
    test_results = models.ForeignKey('framework_data.TestResults', on_delete=models.CASCADE, null=True)
    err_id = models.CharField(max_length=50)
    test = models.ForeignKey('framework_data.Test', on_delete=models.CASCADE, null=True)
    problematic_element_selector = models.CharField(max_length=500)
    problematic_element_position = models.CharField(max_length=50)
    code_snippet = models.TextField()
    # If page gets deleted will be set to null, null values must be handled by the report generator
    pages = models.ManyToManyField('page.Page')
    severity = models.CharField(max_length=20, default='FAIL')
    steps = models.TextField(null=True)
    actual_result = models.CharField(max_length=10000, null=True)
    note = models.CharField(max_length=10000, null=True)
    expected_result = models.CharField(max_length=10000, null=True)
    issue = models.ForeignKey(
        'report.Issue', on_delete=models.CASCADE, null=True, related_name='examples'
    )
    uuid = models.CharField(max_length=40, null=True)
    force_best_practice = models.BooleanField(default=False)
    order_in_issuegroup = models.IntegerField(default=1)
    recommendations = models.CharField(max_length=10000, default='', null=True, blank=True)

    @property
    def title(self):
        orig_data = xlsdata.get_data_for_issue(self.err_id)
        wcag = orig_data['WCAG']
        issue_title = orig_data['issue_title']
        return f'{issue_title} {wcag}'

    class Meta:
        db_table = 'example'


class ExampleScreenshot(models.Model):
    example = models.ForeignKey(Example, on_delete=models.CASCADE)
    screenshot = models.ImageField(null=True, upload_to='images/reports/')

    class Meta:
        db_table = 'example_screenshot'


class PageScreenshot(models.Model):
    screenshot = models.ImageField()
    test_results = models.ForeignKey('framework_data.TestResults', on_delete=models.CASCADE)
    page = models.ForeignKey('page.Page', on_delete=models.CASCADE)

    class Meta:
        db_table = 'page_screenshot'
