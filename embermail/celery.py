import os
from celery import Celery
from celery.schedules import crontab

from django.conf import settings

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "embermail.settings")

# Create an instance of the Celery application
app = Celery("embermail")

# Load the Celery configuration from the Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover and register tasks from Django app modules
app.autodiscover_tasks()

# # Celery Beat Settings
# crontab_hour = getattr(settings, "MAIN_ALGORITHM_RUN_TIME_HOUR", '1')
# crontab_minute = getattr(settings, "MAIN_ALGORITHM_RUN_TIME_MINUTE", '30')
# app.conf.beat_schedule = {
#     'run_main_algorithm': {
#         'task': 'embermail.interface.campaigns.tasks.main_algorithm',
#         # Runs on Every day at 06:00 AM (UTC - 01:30 AM).
#         'schedule': crontab(hour=crontab_hour, minute=crontab_minute),
#         # 'args': (),
#     }
# }
