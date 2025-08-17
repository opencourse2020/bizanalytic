import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

celery_app = Celery('bizanalytic')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks()

celery_app.conf.task_time_limit = 60  # Default hard timeout of 60 seconds
celery_app.conf.task_soft_time_limit = 55 # Default soft timeout of 55 seconds

@celery_app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
