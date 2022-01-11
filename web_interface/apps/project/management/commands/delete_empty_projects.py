from django.core.management.base import BaseCommand

from web_interface.apps.project.models import Project

class Command(BaseCommand):
    help = 'Delete all projects that have never been tested'


    def handle(self, *args, **options):
        projects = Project.objects.filter(last_test=None)
        projects.delete()
        
        print('Deleted ' + str(len(projects)) + ' projects')