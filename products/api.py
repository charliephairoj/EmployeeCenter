"""
API for products
"""
import logging

from tastypie import fields
from tastypie.authorization import Authorization
from tastypie.resources import ModelResource as Resource

from products.models import Model, Configuration, Product


logger = logging.getLogger(__name__)


class ModelResource(Resource):
    class Meta:
        queryset = Model.objects.all()
        resource_name = 'model'
        authorization = Authorization()
        always_return_data = True
        
    def obj_create(self, bundle, **kwargs):
        """
        Overrides the object creation method of the original 
        resource.
        """
        logger.info("Creating model: {0} {1}...".format(bundle.data["model"],
                                                    bundle.data["name"]))
        return super(ModelResource, self).obj_create(bundle, **kwargs)
    
    def obj_update(self, bundle, **kwargs):
        """
        Overrides the object update method of the 
        original resource.
        
        The parent method first so that we can use the object
        in the bundle that has been fully hydrated
        """
        bundle = super(ModelResource, self).update(bundle, **kwargs)
        logger.info("Updating model: {0} {1}...".format(bundle.obj.model,
                                                     bundle.obj.name))
        return bundle
    
    def obj_delete(self, bundle, **kwargs):
        """
        Overrides the object update method of the original resource
        
        The resource is retrieved from the database using the pk
        that is available in the kwargs
        """
        model = Model.objects.get(pk=kwargs['pk'])
        logger.info("Deleting model: {0} {1}...".format(model.model,
                                                    model.name))
        super(ModelResource, self).obj_delete(bundle, **kwargs)
        

class ConfigurationResource(Resource):
    class Meta:
        queryset = Configuration.objects.all()
        resource_name = 'configuration',
        authorization = Authorization()
        always_return_data = True
        
        
class ProductResource(Resource):
    class Meta:
        queryset = Product.objects.all()
        resource_name = 'product',
        authorization = Authorization()
        always_return_data = True
        
        