from django.core.management.base import BaseCommand

from web_interface.apps.job.models import Job
from web_interface.apps.report.models import Issue, ConformanceLevel, SuccessCriteriaLevel
from web_interface.apps.task.models import Task


class Command(BaseCommand):
    help = 'Loads available tests and updates the DB cache'

    def add_arguments(self, parser):
        parser.add_argument('job_name_or_id', type=str)

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('|%s|' % options['job_name_or_id']))

        try:
            job = Job.objects.get(id=int(options['job_name_or_id']))
        except ValueError:
            matching_jobs = Job.objects.filter(name__contains=options['job_name_or_id'])

            if len(matching_jobs) == 0:
                self.stdout.write(self.style.NOTICE('No match'))
                return
            if len(matching_jobs) > 1:
                for job in matching_jobs:
                    self.stdout.write(self.style.NOTICE('%s - %s' % (job.id, job.name)))
                return
            job = matching_jobs[0]

        self.stdout.write(self.style.NOTICE('Cloning job %s' % job.name))
        old_job = Job.objects.get(id=job.id)

        new_job = Job.objects.get(pk=old_job.pk)
        new_job.pk = None
        new_job.name = f'{new_job.name} (Copy)'
        new_job.save()

        test_results = None
        conformance_levels = None
        latest_task = Task.objects.filter(target_job=old_job).latest()

        self.stdout.write(self.style.NOTICE(
            'New job %s, latest task id %s job id %s valid %s'
            % (job.id, latest_task.id, latest_task.target_job.id, latest_task.is_valid)
        ))

        for task__date_started in job.task_set.values_list('date_started', flat=True):
            self.stdout.write(self.style.NOTICE('\ttask %s' % task__date_started))

        if latest_task:
            latest_task.pk = None
            test_results = latest_task.test_results
            if test_results:
                test_results.pk = None
                test_results.save()

                # Copying report params...
                self.stdout.write(self.style.NOTICE('Copying report params...'))
                conformance_levels = ConformanceLevel.objects.filter(test_results=test_results)
                for level in conformance_levels:
                    level.pk = None
                    level.test_results = test_results
                    level.save()

            latest_task.test_results = test_results
            latest_task.target_job = new_job
            latest_task.save()

        try:
            old_test_results = Task.objects.filter(target_job=old_job).latest().test_results
        except AttributeError:
            pass
        else:
            # Copying issue groups...
            for issue in Issue.objects.prefetch_related(
                    'examples', 'examples__examplescreenshot_set'
            ).filter(test_results=old_test_results):
                self.stdout.write(self.style.NOTICE(f'\rCopying issue %s...' % issue.err_id))
                issue.pk = None
                issue.test_results = test_results
                issue.save()
                issue_reloaded = Issue.objects.get(pk=issue.pk)
                for example in issue.examples.all():
                    example.issue = issue_reloaded
                    example.pk = None
                    example.test_results = test_results
                    example.save()
                    for issue_screenshot in example.examplescreenshot_set.all():
                        issue_screenshot.pk = None
                        issue_screenshot.example = example
                        issue_screenshot.save()

                if conformance_levels:
                    old_conformance_level = ConformanceLevel.objects.filter(
                        test_results=test_results,
                        issues=issue_reloaded
                    )
                    if old_conformance_level.count() > 0:
                        conformance_level = ConformanceLevel.objects.get(
                            test_results=test_results,
                            WCAG=old_conformance_level.WCAG
                        )
                        conformance_level.issues.add(issue_reloaded)
                        conformance_level.save()

            counter = 1
            success_criteria_levels = SuccessCriteriaLevel.objects.filter(test_results=old_test_results)
            for success_criteria_level in success_criteria_levels:
                self.stdout.write(
                    self.style.NOTICE('\rCopying success criteria %s/%s...' % (counter, len(success_criteria_levels)))
                )
                success_criteria_level.test_results = test_results
                success_criteria_level.pk = None
                success_criteria_level.save()
                counter += 1

        self.stdout.write(self.style.SUCCESS('Done cloning'))
