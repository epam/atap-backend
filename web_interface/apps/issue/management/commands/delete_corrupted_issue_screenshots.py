from django.core.management.base import BaseCommand

from web_interface.apps.issue.models import ExampleScreenshot


class Command(BaseCommand):
    help = 'Deletes all ExampleScreenshot entries if there are no matching files'

    def handle(self, *args, **options):
        counter = 0
        issue_screenshots = ExampleScreenshot.objects.all()
        for issue_screenshot in issue_screenshots:
            if not issue_screenshot.screenshot.storage.exists(issue_screenshot.screenshot.name):
                self.stdout.write(self.style.WARNING('Removing ExampleScreenshot "%s"' % issue_screenshot.id))
                issue_screenshot.delete()
                counter += 1

        if counter:
            self.stdout.write(self.style.SUCCESS('Successfully deleted %s corrupted ExampleScreenshot entries' % counter))
        else:
            self.stdout.write(self.style.SUCCESS('ExampleScreenshot entries do not need processing'))
