from django.db import models


class TestResults(models.Model):
    """
    A model that is used to conveniently link tests and their results.
    Will be deprecated in the future.
    """

    class Meta:
        db_table = 'test_results'


class Test(models.Model):
    """
    These are the results of a specific test for a specific 'task.Task',
    with a list of faulty elements, their further connection with the 'issue.Issue', etc.
    """
    NOTRUN = 'NOTRUN'
    WARN = 'WARN'
    NOELEMENTS = 'NOELEMENTS'
    ERROR = 'ERROR'
    FAIL = 'FAIL'
    READY = 'READY'
    PASS = 'PASS'

    STATUS_CHOICES = (
        (NOTRUN, 'NOTRUN'),
        (WARN, 'WARN'),
        (NOELEMENTS, 'NOELEMENTS'),
        (ERROR, 'ERROR'),
        (FAIL, 'FAIL'),
        (READY, 'READY'),
        (PASS, 'PASS')
    )

    name = models.CharField(max_length=1000)
    status = models.CharField(choices=STATUS_CHOICES, max_length=20)
    support_status = models.CharField(max_length=20)
    checked_elements = models.TextField(null=True)
    test_results = models.ForeignKey(TestResults, on_delete=models.CASCADE)
    problematic_pages = models.TextField()
    manually = models.BooleanField(default=False)

    class Meta:
        db_table = 'test'


class AvailableTest(models.Model):
    """This is a list of tests that is static per build"""
    name = models.CharField(max_length=200)
    human_name = models.CharField(max_length=300)
    time_data = models.CharField(max_length=300, null=True)
    groups = models.ManyToManyField('framework_data.AvailableTestGroup', related_name='available_tests', blank=True)

    class Meta:
        db_table = 'available_test'


class AvailableTestGroup(models.Model):
    """
    All - All tests;
    Fast Run - ax-core tests and our tests that run quickly (when we collect statistics and add them)
    Critical impact - tests that are necessary to check the site for accessibility according to criteria
                      that are critical for users (bugs are reported as critical). Includes multiple Ax-core tests
    Level A - Tests for Level A Requirements
    AA Level - A test for the AA level requirement.
               If this checkbox is activated, then the Level A checkbox is automatically activated
    Best Practice - tests that are of a recommendatory nature.
                    If this checkbox is not selected, then the Best Practice section will be absent in the report.
    """
    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'available_test_group'


class TestTiming(models.Model):
    name = models.CharField(max_length=1000)
    timestamp = models.DateTimeField(auto_now=True)
    page_size_data = models.CharField(max_length=10000, null=True)  # for several page, if needed
    run_times = models.IntegerField(default=1)

    class Meta:
        db_table = 'test_timing'
