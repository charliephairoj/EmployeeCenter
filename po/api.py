"""
API Resource classes for the
Purchase Order module
"""
import logging
from decimal import *
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError
from tastypie.resources import ModelResource
from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from tastypie.exceptions import NotFound, BadRequest, InvalidFilterError, HydrationError, InvalidSortError, ImmediateHttpResponse, Unauthorized

from po.models import PurchaseOrder, Item
from contacts.models import Supplier
from projects.models import Project
from supplies.models import Supply, Log, Product


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
            
        #Adds a dictionary for the project if it exists
        if bundle.obj.project:
            bundle.data['project'] = {'id': bundle.obj.project.id,
                                      'codename': bundle.obj.project.codename}
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
        
        #Set the project or create a new one
        if "project" in bundle.data:
            try:
                project = Project.objects.get(pk=bundle.data['project']['id'])
            except KeyError, Project.DoesNotExist:
                project = Project()
                project.codename = bundle.data['project']['codename']
                project.save()
                
            bundle.obj.project = project
        
        #Assign the supplier
        #and the terms
        try:
            bundle.obj.supplier = Supplier.objects.get(pk=bundle.data['supplier']['id'])
            bundle.obj.terms = bundle.obj.supplier.terms
            bundle.obj.currency = bundle.obj.supplier.currency
            
            #Conditionally apply discount from supplier or user, with user having priority
            bundle.obj.discount = bundle.obj.supplier.discount
            try:
                discount = int(bundle.data['discount'])
                bundle.obj.discount = discount
            except KeyError:
                pass
                
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
        #Adds the item if it does not exist
        for item in bundle.data['items']:
            try:
                item_obj = bundle.obj.items.get(pk=item['id'], purchase_order=bundle.obj)
                if item['quantity'] != item_obj.quantity:
                    updated = True
                    item_obj.quantity = item['quantity']
                   
                if "discount" in item:
                    updated = True
                    item_obj.discount = item['discount']
                else:
                    if item_obj.discount != 0:
                        item_obj.discount = 0
                        updated = True
                item_obj.supply.supplier = bundle.obj.supplier
                logger.debug("Item ID: {0}, Mid Discount check 1: {1}".format(item_obj.id, item_obj.discount))
                
                item_obj.calculate_total()
                logger.debug("Item IDL {0}, Mid Discount check 2: {1}".format(item_obj.id, item_obj.discount))
                item_obj.save()
            except (KeyError, Item.DoesNotExist):
                updated = True
                #Create a new item
                item_obj = Item.create(supplier=bundle.obj.supplier, **item)
                logger.debug("New Item with discount {0}".format(item))
                item_obj.purchase_order = bundle.obj
                item_obj.save()
            
            if "unit_cost" in item:
                product = Product.objects.get(supply=item_obj.supply, supplier=bundle.obj.supplier)
                if product.cost != Decimal(item['unit_cost']):
                    try:
                        updated = True
                        old_price = product.cost
                        product.cost = Decimal(item['unit_cost'])
                        product.save()
                        item_obj.unit_cost = product.cost
                        
                        item_obj.calculate_total()
                        item_obj.save()
                        logger.debug(item_obj.__dict__)
                        log = Log(supply=item_obj.supply,
                                  supplier=bundle.obj.supplier,
                                  action="PRICE CHANGE",
                                  quantity=None,
                                  cost=product.cost,
                                  message=u"Price change from {0}{2} to {1}{2} for {3} [Supplier: {4}]".format(old_price,
                                                                                                              product.cost,
                                                                                                              bundle.obj.supplier.currency,
                                                                                                              item_obj.supply.description,
                                                                                                              bundle.obj.supplier.name))
                        log.save()
                    except Exception as e:
                        logger.error(e)
                        raise
                    
        
        #Deletes items that have been removed
        server_items = set([i.id for i in bundle.obj.items.all()])
        client_items = set([item['id'] for item in bundle.data['items']])
        logger.debug((server_items, client_items))
        for item_id in server_items.difference(client_items):
            logger.debug(item_id)
            bundle.obj.items.get(pk=item_id).delete()
            
        if updated:
            bundle.obj.revision += 1
            bundle.obj.order_date = datetime.now()
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
        