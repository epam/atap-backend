import os

from celery import Celery
from celery.app.control import Control

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_interface.settings')

app = Celery('web_interface')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

control = Control(app)
