from django.db import models
from django.db.models import Q, UniqueConstraint


class Issue(models.Model):
    err_id = models.CharField(max_length=50)
    test_results = models.ForeignKey(
        'framework_data.TestResults', on_delete=models.CASCADE, related_name='issues'
    )
    priority = models.CharField(max_length=250, null=True)
    techniques = models.TextField(null=True)
    intro = models.TextField(null=True)
    example_shows = models.CharField(max_length=10000, null=True)
    type_of_disability = models.CharField(max_length=400, null=True)
    references = models.TextField(null=True)
    recommendations = models.TextField(null=True)
    name = models.CharField(max_length=500, null=True)
    issue_type = models.CharField(max_length=500, null=True)
    wcag = models.CharField(max_length=50)
    is_best_practice = models.BooleanField()
    labels = models.ManyToManyField('report.IssueLabel', related_name='issues', blank=True)

    class Meta:
        db_table = 'issue'


class Report(models.Model):
    type = models.CharField(max_length=10)
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='reports')
    task = models.ForeignKey('task.Task', on_delete=models.CASCADE)

    class Meta:
        db_table = 'report'


class SummaryParams(models.Model):
    general = models.TextField(null=True)
    testing_standart = models.TextField(null=True)
    testing_type = models.TextField(null=True)
    pages_list_description = models.CharField(max_length=255)

    class Meta:
        db_table = 'summary_params'


class VpatReportParams(models.Model):
    TERMS_STR = '''<p>The terms used in the Conformance Level information are defined as follows:</p>
                <ul>
               <li><b>Supports</b>: The functionality of the product has at least one method that meets the criterion without known defects or meets with equivalent facilitation.</li> 
               <li><b>Partially Supports</b>: Some functionality of the product does not meet the criterion.</li> 
                <li><b>Does Not Support</b>: The majority of product functionality does not meet the criterion.</li> 
                <li><b>Not Applicable</b>: The criterion is not relevant to the product.</li> 
               <li><b>Not Evaluated</b>: The product has not been evaluated against the criterion. This can be used only in WCAG 2.0 Level AAA.</li> 
            </ul>'''

    project = models.ForeignKey('project.Project', null=True, blank=True, on_delete=models.CASCADE)
    job = models.ForeignKey('job.Job', null=True, blank=True, on_delete=models.CASCADE)
    type = models.CharField(max_length=10)
    standart = models.CharField(max_length=255)
    product_description = models.CharField(max_length=255, null=True)
    notes = models.CharField(max_length=255, null=True)
    evaluation_methods = models.CharField(max_length=4000, null=True)
    product_type = models.CharField(max_length=255, default='')
    date = models.DateField(null=True)
    name = models.CharField(max_length=30, default='VPAT')
    product_name_version = models.CharField(max_length=255, default='')
    contact = models.CharField(max_length=255, default='')
    terms = models.CharField(max_length=1000, default=TERMS_STR)
    section_508_note = models.CharField(max_length=255, default='')
    section_en_note = models.CharField(max_length=255, default='')
    applicable_en = models.CharField(max_length=50, default='4,9')
    applicable_508 = models.CharField(max_length=50, default='3')
    wcag_a_note = models.CharField(max_length=255, default='')
    wcag_aa_note = models.CharField(max_length=255, default='')
    wcag_aaa_note = models.CharField(max_length=255, default='')

    class Meta:
        db_table = 'vpat_report_params'

    @property
    def product_types(self) -> list:
        return self.product_type.split(',')


class ConformanceLevelIssue(models.Model):
    issue = models.ForeignKey('report.Issue', related_name='conformance_level_issues', on_delete=models.CASCADE)
    conformance_level = models.ForeignKey('report.ConformanceLevel', related_name='conformance_level_issues',
                                          on_delete=models.CASCADE)

    class Meta:
        db_table = 'conformance_level_issue'


class ConformanceLevel(models.Model):
    WCAG = models.CharField(max_length=250, null=True)
    level = models.CharField(max_length=250, null=True)
    issues = models.ManyToManyField(
        'report.Issue', related_name='conformance_levels', through='report.ConformanceLevelIssue'
    )
    remark = models.CharField(max_length=100, default='')
    test_results = models.ForeignKey('framework_data.TestResults', on_delete=models.CASCADE, null=True)

    class Meta:
        db_table = 'conformance_level'
        unique_together = ('WCAG', 'test_results')

    def issues_names(self) -> list:
        return list(self.issues.values_list('name', flat=True))


class SuccessCriteriaLevel(models.Model):
    criteria = models.CharField(max_length=250, null=True)
    test_results = models.ForeignKey('framework_data.TestResults', on_delete=models.CASCADE, null=True)
    product_type = models.CharField(max_length=250)
    level = models.CharField(max_length=250, null=True)
    remark = models.CharField(max_length=4000, null=True)
    support_level = models.CharField(max_length=3, null=True)

    class Meta:
        db_table = 'success_criteria_level'


class Section508Chapters(models.Model):
    chapter = models.CharField(max_length=250, null=True)
    note = models.CharField(max_length=1000, null=True)
    test_results = models.ForeignKey('framework_data.TestResults', on_delete=models.CASCADE, null=True)
    report = models.ForeignKey(VpatReportParams, on_delete=models.CASCADE, null=True)
    report_type = models.CharField(max_length=10, null=True)
    name = models.CharField(max_length=250, null=True)
    applicable = models.BooleanField(default=True)

    class Meta:
        db_table = 'section_508_chapters'
        unique_together = ('chapter', 'test_results', 'report')


class Section508Criteria(models.Model):
    chapter = models.ForeignKey(Section508Chapters, on_delete=models.CASCADE, null=True)
    criteria = models.CharField(max_length=250, null=True)
    level = models.CharField(max_length=250, null=True)
    remark = models.CharField(max_length=4000, null=True)
    product_type = models.CharField(max_length=250, null=True)

    class Meta:
        db_table = 'section_508_criteria'
        unique_together = ('chapter', 'criteria', 'product_type')


class IssueLabel(models.Model):
    test_results = models.ForeignKey('framework_data.TestResults', on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=250, null=True)
    read_only = models.BooleanField(default=False)  # True only for labels from metadata

    class Meta:
        db_table = 'issue_label'
        constraints = [
            UniqueConstraint(fields=('name', 'read_only', 'test_results'),
                             condition=Q(test_results__isnull=False) & Q(read_only=False),
                             name='unique_test_results_labels'),
            UniqueConstraint(fields=('name', 'read_only'),
                             condition=Q(test_results__isnull=True) & Q(read_only=True),
                             name='unique_read_only_labels'),
        ]
