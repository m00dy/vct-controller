from __future__ import absolute_import

from time import time

from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import get_model
from django.utils import timezone

from controller.utils import is_installed
from controller.utils.time import heartbeat_expires

from .settings import PING_INSTANCES


for instance in PING_INSTANCES:
    # This has to be before Ping class in order to avoid import problems
    if is_installed(instance.get('app')):
        context = {
            'app': instance.get('app'),
            'model': instance.get('model').split('.')[1] }
        exec('from %(app)s.models import %(model)s as model' % context)
        model.add_to_class('pings', generic.GenericRelation('ping.Ping'))


class Ping(models.Model):
    ONLINE = 'ONLINE'
    OFFLINE = 'OFFLINE'
    NODATA = 'NODATA'
    
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    packet_loss = models.PositiveIntegerField(null=True)
    min = models.DecimalField(decimal_places=3, max_digits=9, null=True)
    avg = models.DecimalField(decimal_places=3, max_digits=9, null=True)
    max = models.DecimalField(decimal_places=3, max_digits=9, null=True)
    mdev = models.DecimalField(decimal_places=3, max_digits=9, null=True)
    date = models.DateTimeField(auto_now_add=True, null=True)
    
    content_object = generic.GenericForeignKey()
    
    class Meta:
        ordering = ('-date',)
    
    @classmethod
    def get_state(cls, obj):
        try:
            last = obj.pings.all().order_by('-date')[0]
        except IndexError:
            return cls.NODATA
        settings = cls.get_instance_settings(obj)
        kwargs = {
            'freq': settings.get('schedule'),
            'expire_window': settings.get('expire_window')}
        if time() > heartbeat_expires(last.date, **kwargs):
            return cls.NODATA
        if last.packet_loss == 100:
            return cls.OFFLINE
        return cls.ONLINE
    
    @classmethod
    def get_instance_settings(cls, model, setting=None):
        if not (isinstance(model, unicode) or isinstance(model, str)):
            model = "%s.%s" % (model._meta.app_label, model._meta.object_name)
        for instance in PING_INSTANCES:
            if model == instance.get('model'):
                if setting:
                    return instance.get(setting)
                return instance

