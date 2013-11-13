"""
API file for supplies
"""
from decimal import Decimal
import logging
import json

from django.db.models import Q
from django.conf.urls import url
from tastypie import fields
from tastypie.resources import ModelResource
from tastypie.authorization import DjangoAuthorization
from tastypie.exceptions import Unauthorized

from supplies.models import Supply, Fabric
from contacts.models import Supplier
from supplies.validation import SupplyValidation, FabricValidation


logger = logging.getLogger(__name__)


class SupplyResource(ModelResource):
    
    class Meta:
        queryset = Supply.objects.all()
        resource_name = 'supply'
        always_return_data = True
        validation = SupplyValidation()
        authorization = DjangoAuthorization()
    
    def apply_filters(self, request, applicable_filters):
        obj_list = super(SupplyResource, self).apply_filters(request, applicable_filters)
        
        
        if request.GET.has_key('q'):
            query = request.GET.get('q')
            obj_list = obj_list.filter(Q(supplier__name__icontains=query) | 
                                       Q(description__icontains=query))
        return obj_list
    
    def prepend_urls(self):
        return [
                url(r"^{0}/(?P<pk>\d+)/add$".format(self._meta.resource_name), self.wrap_view('add')),
                url(r"^{0}/(?P<pk>\d+)/subtract".format(self._meta.resource_name), self.wrap_view('subtract'))
                ]
        
    def add(self, request, **kwargs):
        """
        Adds a quantity to the supply
        
        This method checks that the request method is post, and that
        there is both a quantity and an acknowledgement ID
        """
        if not request.method == "POST":
            pass#return self.create
        obj = self._meta.queryset.get(pk=kwargs['pk'])
       
        obj.quantity = round(obj.quantity + float(request.REQUEST.get('quantity')), 2)
        obj.save()
        
        return self.create_response(request, obj.__dict__)
    
    def subtract(self, request, **kwargs):
        """
        Subtracts a quantity to the supply
        
        This method checks that the request method is post, and that
        there is both a quantity and an acknowledgement ID
        """
        
        if not request.method == "POST":
            pass#return self.create
        obj = self._meta.queryset.get(pk=kwargs['pk'])
       
        obj.quantity = round(obj.quantity - float(request.REQUEST.get('quantity')), 2)
        obj.save()
        
        return self.create_response(request, obj.__dict__)
    
    def hydrate(self, bundle):
        """
        Implements the hydrate function 
        """
        try:
            bundle.obj.supplier = Supplier.objects.get(pk=bundle.data['supplier']['id'])
        except KeyError:
            pass
        
        #Change the quantity
        if "quantity" in bundle.data and bundle.obj.pk:
            #Equalize the 2 quantities so that
            #they are easier to work with and compare
            client_quantity = float(bundle.data['quantity'])
            server_quantity = float(bundle.obj.quantity)
            difference = abs(client_quantity - server_quantity)

            #Get the description
            description = bundle.obj.description
            purchasing_units = bundle.obj.purchasing_units
            
            #Checks if quantity is added
            if client_quantity > server_quantity:
                if bundle.request.user.has_perm('supplies.add_quantity'):
                    bundle.obj.quantity = client_quantity
                    logger.info("Added {0}{1} to {2} inventory".format(difference,
                                                                       purchasing_units,
                                                                       description))
                else:
                    bundle.data['quantity'] = server_quantity
                    bundle.data['quantity'] = server_quantity
                    warning = "{0} is not authorized to add to the quantity of Fabric {1}".format(bundle.request.user.username,
                                                                                                  bundle.obj.description)
                    logger.warn(warning)
                    #raise Unauthorized("User does not have authorization to add to inventory.")
                
            #Checks if quantity was subtracted
            elif client_quantity < server_quantity:
                if bundle.request.user.has_perm('supplies.subtract_quantity'):
                    bundle.obj.quantity = client_quantity
                    logger.info("Subtracted {0}{1} from {2} inventory".format(difference,
                                                                       purchasing_units,
                                                                       description))
                else:
                    bundle.data['quantity'] = server_quantity
                    warning = "{0} is not authorized to subtract from the quantity of Fabric {1}".format(bundle.request.user.username,
                                                                                                         bundle.obj.description)
                    logger.warn(warning)
                    #raise Unauthorized("User does not have authorization to subtract from inventory.")
            
        return bundle
    
    def dehydrate(self, bundle):
        """
        Implements the dehydrate method to manipulate data
        before it is returned to the client
        """
        if not bundle.request.user.has_perm('supplies.view_cost'):
            try:
                del bundle.data['cost']
            except KeyError:
                pass
        
        #Attack the image if it exists
        if bundle.obj.image:
            bundle.data['image'] = {'url': bundle.obj.image.generate_url()}
            
        return bundle
    
    
class FabricResource(SupplyResource):
    #supplier = fields.ToOneField('contacts.api.SupplierResource', 'supplier', full=True)
    class Meta:
        queryset = Fabric.objects.all()
        resource_name = 'fabric'
        #validation = FabricValidation()
        authorization = DjangoAuthorization()
        always_return_data = True
        
    def apply_filters(self, request, applicable_filters):
        obj_list = super(FabricResource, self).apply_filters(request, applicable_filters)
        
        
        if request.GET.has_key('q'):
            query = request.GET.get('q')
            obj_list = obj_list.filter(Q(supplier__name__icontains=query) | 
                                       Q(description__icontains=query) |
                                       Q(pattern__icontains=query) |
                                       Q(color__icontains=query))
        return obj_list
    

    
    
    
    
    
