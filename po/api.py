"""
API Resource classes for the
Purchase Order module
"""
import logging
from decimal import *

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError
from tastypie.resources import ModelResource
from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from tastypie.exceptions import NotFound, BadRequest, InvalidFilterError, HydrationError, InvalidSortError, ImmediateHttpResponse, Unauthorized

from po.models import PurchaseOrder, Item
from contacts.models import Supplier


logger = logging.getLogger(__name__)


class PurchaseOrderResource(ModelResource):
    items = fields.ToManyField('po.api.ItemResource', 'items', related_name="purchase_order",
                               readonly=True, null=True, full=True)
    supplier = fields.ToOneField('contacts.api.SupplierResource', 'supplier',
                                 readonly=True, full=True)
    class Meta:
        resource_name = "purchase-order"
        queryset = PurchaseOrder.objects.all().order_by('-id')
        always_return_data = True
        authorization = DjangoAuthorization() 
        
    def hydrate(self, bundle):
        """
        Prepares the data before it is applied to the models
        """
        
        if bundle.obj.pk:
            try:
                #Updates the status of the items in the order
                for item in bundle.data['items']:
                    po_item = Item.objects.get(pk=item['id'])
                    po_item.status = item['status']
                    po_item.save()
            except:
                pass
            
        return bundle
    
    def dehydrate(self, bundle):
        """
        Get a single obj
        """
        #Add URLS for the acknowledgement
        #and the production pdf to the data
        #bundle
        if 'pdf' in bundle.request.GET.keys():
            try:
                bundle.data['pdf'] = {'url': bundle.obj.pdf.generate_url()}
            except AttributeError as e: 
                logger.warn(e)
                logger.warn('Missing pdf')
            
        return bundle
        
    def obj_create(self, bundle, **kwargs):
        """
        Creates a new purchase order
        """
        logger.info("Creating a purchase order")
        #Create the object
        bundle.obj = PurchaseOrder()
        #Hydreate the obj
        bundle = self.full_hydrate(bundle, **kwargs)
        #Assign the employee
        bundle.obj.employee = bundle.request.user
        #Assign the supplier
        #and the terms
        try:
            bundle.obj.supplier = Supplier.objects.get(pk=bundle.data['supplier']['id'])
            bundle.obj.terms = bundle.obj.supplier.terms
            bundle.obj.currency = bundle.obj.supplier.currency
            bundle.obj.discount = bundle.obj.supplier.discount
        except KeyError:
            logger.error("Missing supplier's ID")
            raise ValueError("Expecting the supplier's ID.")
        except Supplier.DoesNotExist:
            logger.error("The supplier ID#{0} no longer exists.".format(bundle.data["supplier"]["id"]))
            raise 
        #Create the items 
        self.items = [Item.create(supplier=bundle.obj.supplier, **item_data) for item_data in bundle.data['items']]
        
        #for item in self.items:
        #    item.supplier = bundle.obj.supplier
       
        bundle = self.save(bundle)
        
        for item in self.items:
            item.purchase_order = bundle.obj
            item.save()
            
        logger.debug("Calculating totals...")
        bundle.obj.calculate_total()
        bundle.obj.save()

        #Create a pdf to be uploaded 
        #to the S3 service. Then generate 
        #a url for the data that will be returned to the customer
        logger.info("Creating pdf for purchase order #{0}".format(bundle.obj.id))
        bundle.obj.create_and_upload_pdf()
        bundle.data["pdf"] = {"url": bundle.obj.pdf.generate_url()}
        
        return bundle
    
    def obj_update(self, bundle, **kwargs):
        """
        Determines what to do if the purchase order is updated
        """
        #update flag
        updated = False
        logger.debug('hhhiashdfiasdf')
        #Get the bundle obj and data
        if not bundle.obj or not self.get_bundle_detail_data(bundle):
            try:
                lookup_kwargs = self.lookup_kwargs_with_identifiers(bundle, kwargs)
            except:
                # if there is trouble hydrating the data, fall back to just
                # using kwargs by itself (usually it only contains a "pk" key
                # and this will work fine.
                lookup_kwargs = kwargs

            try:
                bundle.obj = self.obj_get(bundle=bundle, **lookup_kwargs)
            except ObjectDoesNotExist:
                raise NotFound("A model instance matching the provided arguments could not be found.")
        
        #Update order details
        try:
            if bundle.obj.discount != int(bundle.data['discount']):
                bundle.obj.discount = bundle.data['discount']
                updated = True
        except KeyError:
            pass
        
        #Check if the number of items have changed
        if bundle.obj.items.count() != len(bundle.data['items']):
            updated = True
            
        #Check if quantities have changed and whether item exists
        for item in bundle.data['items']:
            try:
                item_obj = bundle.obj.items.get(pk=item['id'], purchase_order=bundle.obj)
                if item['quantity'] != item_obj.quantity:
                    updated = True
                    item_obj.supply.supplier = bundle.obj.supplier
                    item_obj.quantity = item['quantity']
                    item_obj.calculate_total()
                    item_obj.save()
            except (KeyError, Item.DoesNotExist):
                updated = True
                #Create a new item
                item_obj = Item.create(supplier=bundle.obj.supplier, **item)
                item_obj.purchase_order = bundle.obj
                item_obj.save()
        
        if updated:
            bundle.obj.calculate_total()
            bundle.obj.save()
            bundle.obj.create_and_upload_pdf()
            bundle.data["pdf"] = {"url": bundle.obj.pdf.generate_url()}
            
        return bundle
    
        
class ItemResource(ModelResource):
    class Meta:
        resource_name = "purchase-order-item"
        queryset = Item.objects.all()
        always_return_data = True
        authorization = DjangoAuthorization()
        allowed_methods = ['get', 'put', 'patch']
        
    def dehydrate(self, bundle):
        """
        Prepare data before it is returned to the client
        """
        bundle.data['units'] = bundle.obj.supply.units
        
        return bundle
        