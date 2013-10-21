"""
API for products
"""
import logging

from django.db.models import Q
from tastypie import fields
from tastypie.authorization import Authorization
from tastypie.resources import ModelResource as Resource

from products.models import Model, Configuration, Upholstery, Pillow, ModelImage, Table
from products.validation import *


logger = logging.getLogger(__name__)


class ModelResource(Resource):
    images = fields.ManyToManyField('media.api.S3ObjectResource', 'images', full=True,
                                    readonly=True)
    class Meta:
        queryset = Model.objects.all()
        resource_name = 'model'
        authorization = Authorization()
        always_return_data = True 
        validation = ModelValidation()
        
    def apply_filters(self, request, applicable_filters):
        """
        Applys filters to the query set.
        
        The parent method is called and then we search the
        name of the model if the query exists
        """
        obj_list = super(ModelResource, self).apply_filters(request, applicable_filters)
        
        if request.GET.has_key('q'):
            query = request.GET.get('q')
            obj_list = obj_list.filter(Q(name__icontains=query) |
                                       Q(model__icontains=query) |
                                       Q(collection__icontains=query))
            
        return obj_list
        
    def obj_create(self, bundle, **kwargs):
        """
        Overrides the object creation method of the original 
        resource.
        """
        logger.info("Creating model...")

        return super(ModelResource, self).obj_create(bundle, **kwargs)
    
    def obj_update(self, bundle, **kwargs):
        """
        Overrides the object update method of the 
        original resource.
        
        The parent method first so that we can use the object
        in the bundle that has been fully hydrated
        """
        logger.info("Updating model...")
        
        return super(ModelResource, self).obj_update(bundle, **kwargs)
    
    def obj_delete(self, bundle, **kwargs):
        """
        Overrides the object update method of the original resource
        
        The resource is retrieved from the database using the pk
        that is available in the kwargs
        """
        logger.info("Deleting model...")
        
        super(ModelResource, self).obj_delete(bundle, **kwargs)
        
        
class ModelImageResource(Resource):
    class Meta:
        queryset = ModelImage.objects.all()
        resource_name= 'model/image'
        authorization = Authorization()
        allowed = ['post']
        
        
class PillowResource(Resource):
    class Meta:
        queryset = Pillow.objects.all()
        resource_name = 'pillow'
        always_return_data = True
        authorization = Authorization()
        
                    
class ConfigurationResource(Resource):
    class Meta:
        queryset = Configuration.objects.all()
        resource_name = 'configuration'
        authorization = Authorization()
        always_return_data = True
        validation = ConfigurationValidation()
    
    def apply_filters(self, request, applicable_filters):
        """
        Applys filters to the query set.
        
        The parent method is called and then we search the
        name of the configuration if the query exists
        """
        obj_list = super(ConfigurationResource, self).apply_filters(request, applicable_filters)
        
        if request.GET.has_key('q'):
            query = request.GET.get('q')
            obj_list = obj_list.filter(Q(configuration__icontains=query))
            
        return obj_list
    
    def obj_create(self, bundle, **kwargs):
        """
        Overrides the object create method
        """
        logger.info("Creating new configuration...")
        
        return super(ConfigurationResource, self).obj_create(bundle, **kwargs)
    
    def obj_update(self, bundle, **kwargs):
        """
        Overrides the object update method
        """
        logger.info("Updating configuration...")
        
        return super(ConfigurationResource, self).obj_update(bundle, **kwargs)
    
    def obj_delete(self, bundle, **kwargs):
        """
        Overrides the object delete method
        """
        configuration = Configuration.objects.get(pk=kwargs['pk'])
        logger.info("Deleting configuration: {0}...".format(configuration.configuration))
        
        super(ConfigurationResource, self).obj_delete(bundle, **kwargs)
        

class UpholsteryResource(Resource):
    model = fields.ToOneField('products.api.ModelResource', 'model', full=True, readonly=True)
    configuration = fields.ToOneField('products.api.ConfigurationResource', 'configuration', full=True,
                                      readonly=True)
    #pillows = fields.ToManyField('products.api.PillowResource', 'pillows', full=True, readonly=True)
    
    class Meta:
        queryset = Upholstery.objects.all()
        resource_name = 'upholstery'
        authorization = Authorization()
        always_return_data = True
        validation = UpholsteryValidation()
        
    def hydrate(self, bundle):
        """
        Implement the hydrate method to set additional model datat
        """
        #Set model if not the same
        model = Model.objects.get(pk=bundle.data['model']['id'])
        logger.info("Setting model as: {0} {1}".format(model.model, 
                                                       model.name))
        bundle.obj.model = model
            
        #Set the configuration if not the same
        configuration = Configuration.objects.get(pk=bundle.data['configuration']['id'])
        logger.info("Setting configuration as: {0}".format(configuration.configuration))
        bundle.obj.configuration = configuration
        
        #Set other attribute for this resources that
        #are a shared attribute of the parent resource
        #and that are not set explicit by the user submitted
        #data
        bundle.obj.type = 'upholstery'
        bundle.obj.description = "{0} {1}".format(model.model,
                                                  configuration.configuration)
                
        return bundle
    
    def apply_filters(self, request, applicable_filters):
        """
        Applys filters to the query set.
        
        The parent method is called and then we search the
        name of the upholstery if the query exists
        """
        obj_list = super(UpholsteryResource, self).apply_filters(request, applicable_filters)
        
        if request.GET.has_key('q'):
            query = request.GET.get('q')
            obj_list = obj_list.filter(Q(description__icontains=query) |
                                       Q(model__model__icontains=query) |
                                       Q(model__name__icontains=query) |
                                       Q(configuration__configuration__icontains=query))
            
        return obj_list
        
    def obj_create(self, bundle, **kwargs):
        """
        Implement the obj_create method 
        """
        logger.info("Creating new upholstery...")
        bundle = super(UpholsteryResource, self).obj_create(bundle, **kwargs)
        
        self.hydrate_pillows(bundle)
        return bundle
    
    def obj_update(self, bundle, **kwargs):
        """
        Implement the obj_update method
        """
        logger.info("Updating upholstery...")
        bundle = super(UpholsteryResource, self).obj_update(bundle, **kwargs)
        
        self.hydrate_pillows(bundle)
        return bundle
        
    def obj_delete(self, bundle, **kwargs):
        """
        Implement the obj_delete method
        """
        upholstery = Upholstery.objects.get(pk=kwargs['pk'])
        logger.info("Deleting upholstery:{0} {1} {2}...".format(upholstery.id,
                                                             upholstery.model.model,
                                                             upholstery.configuration.configuration))
        
        super(UpholsteryResource, self).obj_delete(bundle, **kwargs)

    def hydrate_pillows(self, bundle):
        """
        Hydrate the pillows for the uphostery
        
        The method will check if the data in the bundle
        has a key 'pillows'. If it does it will go through
        each dict in the array and update the pillow or create a new one if it 
        does not exist. 
        
        If 'pillows' is not in bundle.data then the method will
        check all {type}_pillow keys for sub dictionaries
        """
        #Check for 'pillows' in the data container
        if "pillows" in bundle.data:
            
            #Loops through all the pillows and
            #either updates or creates a pillow
            for pillow in bundle.data['pillows']:
                self._create_or_update_pillow(product=bundle.obj, 
                                              pillow_type=pillow['type'], 
                                              quantity=pillow['quantity'])
                
        
        #Check for pillows individually by type
        else:
            for pillow_type in ["back", "accent", "corner", "lumbar"]:
                key = "{0}_pillow".format(pillow_type)
                if key in bundle.data:
                    self._create_or_update_pillow(product=bundle.obj, 
                                                  pillow_type=pillow_type,
                                                  quantity=bundle.data[key])
            
        return bundle
    
    def _create_or_update_pillow(self, product=None, pillow_type=None, quantity=None):
        """
        Updates an existing pillow or creates a new one
        """
        #Retrieves the pillow by searhing for the type and 
        #the corresponding product id 
        try:
            pillow = Pillow.objects.get(product_id=product.id,
                                        type=pillow_type)
            pillow.quantity = quantity
            pillow.save()
        #If a pillow of the corresponding type and product id
        #is not a found a new one is made with the specified
        #type, quantity, and product id
        except Pillow.DoesNotExist as e:
            logger.info("Creating a new {0} pillow for Product ID: {1}".format(pillow_type,
                                                                   product.id))
            pillow = Pillow(type=pillow_type, quantity=quantity)
            pillow.product = product
            pillow.save()
            
            
class TableResource(Resource):
    model = fields.ToOneField('products.api.ModelResource', 'model', full=True,
                              readonly=True)
    configuration = fields.ToOneField('products.api.ConfigurationResource', 'configuration', full=True,
                                      readonly=True)
    
    class Meta:
        queryset = Table.objects.all()
        resource_name = 'table'
        authorization = Authorization()
        always_return_data = True
        validation = TableValidation()
        
    def hydrate(self, bundle):
        """
        Implements the hydrate method
        """
        #Set model if not the same
        model = Model.objects.get(pk=bundle.data['model']['id'])
        logger.info("Setting model as: {0} {1}".format(model.model, 
                                                       model.name))
        bundle.obj.model = model
            
        #Set the configuration if not the same
        configuration = Configuration.objects.get(pk=bundle.data['configuration']['id'])
        logger.info("Setting configuration as: {0}".format(configuration.configuration))
        bundle.obj.configuration = configuration
        
        #Set other attribute data specific to tables
        bundle.obj.description = "{0} {1}".format(model.model, configuration.configuration)
        bundle.obj.type = 'table'
        
        return bundle
        
    def apply_filters(self, request, applicable_filters):
        """
        Applys filters to the query set.
        
        The parent method is called and then we search the
        name of the upholstery if the query exists
        """
        obj_list = super(TableResource, self).apply_filters(request, applicable_filters)
        
        if request.GET.has_key('q'):
            query = request.GET.get('q')
            obj_list = obj_list.filter(Q(description__icontains=query) |
                                       Q(model__model__icontains=query) |
                                       Q(model__name__icontains=query) |
                                       Q(configuration__configuration__icontains=query))
            
        return obj_list
    
    def obj_create(self, bundle, **kwargs):
        """
        Implements the obj_create method
        """
        logger.info("Creating a new table...")

        return super(TableResource, self).obj_create(bundle, **kwargs)
    
    def obj_update(self, bundle, **kwargs):
        """
        Implemenets the obj_update method
        """
        logger.info("Updating a table...")
        
        return super(TableResource, self).obj_update(bundle, **kwargs)
    
    def obj_delete(self, bundle, **kwargs):
        """
        Implements the obj_delete method
        """
        table = Table.objects.get(pk=kwargs['pk'])
        logger.info("Deleting table {0}...".format(table.description))
        
        super(TableResource, self).obj_delete(bundle, **kwargs)        
        
            
        