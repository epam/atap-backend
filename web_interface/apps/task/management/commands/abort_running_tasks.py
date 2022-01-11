from django.core.management.base import BaseCommand
from django.db.models import Q

from web_interface.apps.task.models import Task
from web_interface.apps.task.tasks import abort_task


class Command(BaseCommand):
    help = 'Abort all running tasks and tasks in queue'

    def handle(self, *args, **options) -> None:
        tasks = Task.objects.filter(Q(status=Task.RUNNING) | Q(status=Task.QUEUED))
        for task in tasks:
            abort_task(task)
        self.stdout.write(self.style.NOTICE('All running tasks and tasks in queue are aborted'))
