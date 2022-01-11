from django.core.management.base import BaseCommand
from web_interface.apps.project.models import Project
from web_interface.apps.framework_data.models import TestResults
from datetime import datetime
from django.utils import timezone
import pytz


class Command(BaseCommand):
    help = 'Delete all projects that have been tested before date'


    def add_arguments(self, parser):
        parser.add_argument('date', type=str)


    def handle(self, *args, **options):
        date = options['date']
        date = datetime.strptime(date, '%Y-%m-%d')
        date = date.replace(tzinfo=pytz.utc)

        projects = Project.objects.filter(last_test__lt=date)
        for project in projects:
            TestResults.objects.filter(task__target_job__project=project).delete()
            project.delete()
        
        print('Deleted ' + str(len(projects)) + ' projects')