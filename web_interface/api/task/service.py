from web_interface.apps.task.models import SitemapTask
from web_interface.apps.task.tasks import kill_task
from web_interface.celery import control


def abort_sitemap_task(sitemap_task: SitemapTask) -> None:
    control.revoke(sitemap_task.celery_task_id, terminate=True)
    # Schedule a force kill if it does not shut down in 10s
    kill_task.apply_async((sitemap_task.celery_task_id,), countdown=10)
    sitemap_task.delete()
