REQUIRED_APPS = ['issues']

from django.db.models.loading import get_model

from controller.utils import plugins


class ResourcePlugin(object):
    name = ''
    unit = ''
    max_sliver = 0
    dflt_sliver = 0
    producers = []
    consumers = []
    
    __metaclass__ = plugins.PluginMount
    
    @classmethod
    def get_producers_models(cls):
        return cls._get_related_models('producers')
    
    @classmethod
    def get_consumers_models(cls):
        return cls._get_related_models('consumers')
    
    @classmethod
    def get_resources_for_producer(cls, producer):
        return cls._get_resources_by_type(producer, 'producers')
    
    @classmethod
    def get_resources_for_consumer(cls, consumer):
        return cls._get_resources_by_type(consumer, 'consumers')
    
    @classmethod
    def get(cls, name):
        for resource in cls.plugins:
            if resource.name == name:
                return resource
        raise KeyError('Resource with name %s can not be found' % name)
    
    @classmethod
    def _get_related_models(cls, type):
        models = set()
        for resource in cls.plugins:
            for related in getattr(resource, type):
                if related:
                    models.add(get_model(*related.split('.')))
        return models
    
    @classmethod
    def _get_resources_by_type(cls, model, type):
        resources = []
        opts = model._meta
        model = "%s.%s" % (opts.app_label, opts.object_name)
        for resource in cls.plugins:
            if model in getattr(resource, type):
                resources.append(resource)
        return resources