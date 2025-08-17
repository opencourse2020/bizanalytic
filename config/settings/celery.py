import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

celery_app = Celery('bizanalytic')
celery_app.config_from_object('django.conf:config.settings.production', namespace='CELERY')
celery_app.autodiscover_tasks()
