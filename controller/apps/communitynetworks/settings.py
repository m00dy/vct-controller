from celery.task.schedules import crontab
from django.conf import settings

ugettext = lambda s: s

# Cache node_db every day at 2 AM
COMMUNITYNETWORKS_CACHE_NODE_DB_CRONTAB = getattr(settings, 'COMMUNITYNETWORKS_CACHE_NODE_DB_CRONTAB', crontab(minute=0, hour=2))