#from celery.task.schedules import crontab
from django.conf import settings

ugettext = lambda s: s


STATE_LOCK_DIR = getattr(settings, 'STATE_LOCK_DIR', '/dev/shm/')


STATE_NODESTATE_URI = getattr(settings, 'STATE_NODESTATE_URI',
    'http://[%(mgmt_addr)s]/confine/api/node/')

STATE_NODESTATE_SCHEDULE = getattr(settings, 'STATE_NODESTATE_SCHEDULE', 300)

# Percentage
STATE_NODESTATE_EXPIRE_WINDOW = getattr(settings, 'STATE_NODESTATE_EXPIRE_WINDOW', 150)


STATE_SLIVERSTATE_URI = getattr(settings, 'STATE_SLIVERSTATE_URI',
    'http://[%(mgmt_addr)s]/confine/api/slivers/%(object_id)d')

STATE_SLIVERSTATE_SCHEDULE = getattr(settings, 'STATE_SLIVERSTATE_SCHEDULE', 300)

# Percentage
STATE_SLIVERSTATE_EXPIRE_WINDOW = getattr(settings, 'STATE_SLIVERSTATE_EXPIRE_WINDOW', 150)