"""
API for shipping module
"""
import logging
import dateutil

from django.contrib.auth.models import User
from tastypie import fields
from tastypie.resources import ModelResource
from tastypie.authorization import Authorization

from shipping.models import Shipping, Item
from acknowledgements.models import Acknowledgement as Ack


logger = logging.getLogger(__name__)


class ShippingResource(ModelResource):
    customer = fields.ToOneField('contacts.api.CustomerResource', 'customer', full=True,
                                 readonly=True)
    class Meta:
        queryset = Shipping.objects.all().order_by('-id')
        resource_name = 'shipping'
        always_return_data = True
        authorization = Authorization()
    
    def dehydrate(self, bundle):
        """
        Implements a dehydrate method to prepare the data
        for the resource before it is returned to the client
        """
        if bundle.request.GET.get('pdf'):
            print bundle.data
            print bundle.obj.pdf.generate_url()
            bundle.data['pdf'] = {'url': bundle.obj.pdf.generate_url()}
           
                
        return bundle
        
    def obj_create(self, bundle, **kwargs):
        """
        Implements the creation method for shipping
        """
        logger.info("Creating the shipping manifest...")
        bundle.obj = Shipping()
        
        #hydration
        bundle = self.full_hydrate(bundle, **kwargs)
        
        #Sets the acknowledgement
        try:
            bundle.obj.acknowledgement = Ack.objects.get(pk=bundle.data['acknowledgement']['id'])
        except (KeyError, Ack.DoesNotExist):
            logger.error("Missing acknowledgement ID.")
            raise
        
        #Set the employee
        try:
            bundle.obj.employee = User.objects.get(pk=bundle.data['employee']['id'])
        except (KeyError, User.DoesNotExist) as e:
            bundle.obj.employee = bundle.request.user
            
        #Sets the customer
        bundle.obj.customer = bundle.obj.acknowledgement.customer
        
        #Sets the delivery date
        bundle.obj.delivery = bundle.data['delivery_date']
        
        bundle.obj.save()
        
        bundle.obj.process_items(bundle.data['items'])
        
        #Creates a pdf and then uploads it
        logger.info("Creating pdf...")
        bundle.obj.create_and_upload_pdf()
        bundle.data['pdf'] = {'url': bundle.obj.pdf.generate_url()}
        return bundle
    
    def obj_update(self, bundle, **kwargs):
        """
        Implements the obj update at the user level
        
        We only allow certain fields to be modified.
        """
        logger.info("Updating the shipping manifest...")
        #Retrieve the shipping manifest of send out an error
        try:
            bundle.obj = Shipping.objects.get(pk=kwargs['pk'])
        except Shipping.DoesNotExist as e:
            logger.error("Could not find shipping manifest {0}.".format(kwargs['pk']))
        
        
        self.full_hydrate(bundle)
        
        bundle = self.save(bundle)
        
        logger.info("Creating an updated pdf of the shipping manifest...")
        bundle.obj.create_and_upload_pdf()
        
        return bundle
    

class ItemResource(ModelResource):
    class Meta:
        queryset = Item.objects.all()
        resource_name = 'shipping/item'
        always_return_data = True
        authorization = Authorization()
        
            