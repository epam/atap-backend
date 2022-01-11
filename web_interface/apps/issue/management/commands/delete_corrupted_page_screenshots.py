from django.core.management.base import BaseCommand

from web_interface.apps.issue.models import PageScreenshot


class Command(BaseCommand):
    help = 'Deletes all PageScreenshot entries if there are no matching files'

    def handle(self, *args, **options):
        counter = 0
        page_screenshots = PageScreenshot.objects.all()
        for page_screenshot in page_screenshots:
            if not page_screenshot.screenshot.storage.exists(page_screenshot.screenshot.name):
                self.stdout.write(self.style.WARNING('Removing PageScreenshot "%s"' % page_screenshot.id))
                page_screenshot.delete()
                counter += 1

        if counter:
            self.stdout.write(self.style.SUCCESS('Successfully deleted %s corrupted PageScreenshot entries' % counter))
        else:
            self.stdout.write(self.style.SUCCESS('PageScreenshot entries do not need processing'))
