"""
API file for supplies
"""
from decimal import Decimal
import time
import logging
import json
import re

from django.db.models import Q
from django.conf.urls import url
from tastypie import fields
from tastypie.resources import ModelResource
from tastypie.authorization import DjangoAuthorization
from tastypie.exceptions import Unauthorized

from supplies.models import Supply, Fabric, Product, Log
from contacts.models import Supplier
from supplies.validation import SupplyValidation, FabricValidation
from utilities.http import save_upload
from auth.models import S3Object
from media.stickers import StickerPage


logger = logging.getLogger(__name__)


class SupplyResource(ModelResource):
    #suppliers = fields.ToManyField('contacts.api.SupplierResource', 'suppliers',
    #                             readonly=True, full=True)
    
    class Meta:
        queryset = Supply.objects.all()
        resource_name = 'supply'
        always_return_data = True
        validation = SupplyValidation()
        authorization = DjangoAuthorization()
        ordering = ['image']
        filtering = {'upc': 'exact'}
        #fields = ['purchasing_units', 'description', 'cost', 'id', 'pk']
    
    def apply_filters(self, request, applicable_filters):
        obj_list = super(SupplyResource, self).apply_filters(request, applicable_filters)
        
        obj_list = obj_list.exclude(type='prop')
        obj_list = obj_list.exclude(type='Prop')
        
        if request.GET.has_key('q'):
            query = request.GET.get('q')
            obj_list = obj_list.filter(Q(product__supplier__name__icontains=query) | 
                                       Q(description__icontains=query))
        
        if request.GET.has_key('supplier_id'):
            s_id = request.GET.get('supplier_id')
            obj_list = obj_list.filter(product__supplier_id=s_id)
        
        if request.GET.has_key('upc'):
            upc_id = request.GET.get('upc')
            print upc_id
            obj_list = obj_list.filter(product__upc=upc_id).distinct('product__upc')
        
        if "Administrator" in [g.name for g in request.user.groups.all()]:
            pass#logger.debug('An admin')
        else:
            obj_list = obj_list.filter(admin_only=False)
    
        return obj_list
    
    def prepend_urls(self):
        return [
                url(r"^{0}/image$".format(self._meta.resource_name), self.wrap_view('process_image')),
                url(r"^{0}/type".format(self._meta.resource_name), self.wrap_view('type')),
                url(r"^{0}/(?P<pk>\d+)/subtract".format(self._meta.resource_name), self.wrap_view('subtract')),
                url(r"^{0}/(?P<pk>\d+)/add$".format(self._meta.resource_name), self.wrap_view('add')),
                ]
    def hydrate(self, bundle):
        """
        Implements the hydrate function 
        """
        
        #Takes supplier and add to supplier list in data
        if "supplier" in bundle.data:
            try:
                suppliers = bundle.data['suppliers']
            except KeyError:
                bundle.data['suppliers'] = []
                suppliers = []
            
            if bundle.data['supplier']['id'] not in [s['id'] for s in suppliers]:
                bundle.data['suppliers'].append(bundle.data['supplier'])
                del bundle.data['supplier']
        
        #Adds new types
        try:
            if bundle.data['type'].lower() == 'custom':
                bundle.obj.type = bundle.data['custom-type']
                del bundle.data['custom-type']
            else:
                bundle.obj.type = bundle.data['type']
                
            bundle.data['type'] = bundle.obj.type
        except KeyError as e:
            logger.warn(e)
            
        
            
        #Adds the image
        if "image" in bundle.data:
            try:
                bundle.obj.image = S3Object.objects.get(pk=bundle.data['image']['id'])
            except KeyError:
                #Create a new S3object for the image
                s3_obj = S3Object()
                s3_obj.key = bundle.data['image']['key']
                s3_obj.bucket = bundle.data['image']['bucket']
                s3_obj.save()
                
                bundle.obj.image = s3_obj
            except S3Object.DoesNotExist:
                raise
        
        """
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
        """
        
        return bundle
    
    def dehydrate(self, bundle):
        """
        Implements the dehydrate method to manipulate data
        before it is returned to the client
        """
        #Replaces custom-type with type after supply creation
        if "custom-type" in bundle.data:
            bundle.data['type'] = bundle.obj.type
            del bundle.data['custom-type']
        
        #Dehydrates the suppliers information if 
        #requesting a single resource, if creating a new resource
        #or updating a single resource
        if re.search("api/v1/supply/(w+\-)?\d+", bundle.request.path) or bundle.request.method == 'POST' or bundle.request.method == 'PUT':
            bundle.data['suppliers'] = [self.dehydrate_supplier(bundle, supplier) for supplier in bundle.obj.suppliers.all()]

            if not bundle.obj.sticker:
                sticker_page = StickerPage(code="DRS-{0}".format(bundle.obj.id), 
                                           description=bundle.obj.description)
                filename = sticker_page.create("DRS-{0}".format(bundle.obj.id))    
                stickers = S3Object.create(filename, 
                                           "supplies/stickers/{0}".format(filename), 
                                           'document.dellarobbiathailand.com', 
                                           encrypt_key=True)
                bundle.obj.sticker = stickers
                bundle.obj.save()
                
            bundle.data['sticker'] = {'url':bundle.obj.sticker.generate_url()}
        #If getting a list
        else:
            bundle.data['suppliers'] = [{'name': supplier.name,
                                         'id': supplier.id} for supplier in bundle.obj.suppliers.all()]
        
        #Merging product data from a supplier with the resource
        #if gettings supplies for a single supplier
        if bundle.request.GET.has_key('supplier_id'):
            
            #Set the supply's supplier to using 
            #objects internals to get info
            bundle.obj.supplier = Supplier.objects.get(pk=bundle.request.GET.get('supplier_id'))
            bundle.data.update({'purchasing_units': bundle.obj.purchasing_units,
                                'cost': bundle.obj.cost,
                                'reference': bundle.obj.reference,
                                'upc': bundle.obj.upc})
        if bundle.obj.image:
            try:
                bundle.data['image'] = {'id': bundle.obj.image.id,
                                        'url': bundle.obj.image.generate_url(3600)}
            except (AttributeError, KeyError) as e:
                logger.warn(e)
                
        return bundle
    
    def obj_create(self, bundle, **kwargs):
        """
        Creates the supply, and then respectively 
        creates the intermediary product instance for the
        many to many relationship with suppliers
        
        We must separate the suppliers data before calling the parent 
        obj_create method
        """
        
        try:
            suppliers = bundle.data['suppliers']
        except KeyError:
            suppliers = [bundle.data['supplier']]
        
        #Initial supply creation
        bundle = super(SupplyResource, self).obj_create(bundle, **kwargs)
        
        #Creates products to establish supplier/supply relationship
        for supplier in suppliers:
            #Gets or creates a new product
            try:
                product = Product(supply=bundle.obj, supplier=Supplier.objects.get(pk=supplier['id']))
            except Product.DoesNotExist as e:
                product = Product(supplier=Supplier.objects.get(pk=supplier['id']),
                                  supply=bundle.obj)
            product = self.hydrate_product(product=product, bundle=bundle, **supplier)
            product.save()
        
        return bundle
    
    def obj_update(self, bundle, **kwargs):
        """
        Updates the supply, the product relationship witht the supplier
        
        Extra suppliers before the parent obj_update method destroys it.
        """
        #Get suppliers data before erased by parent method
        suppliers = bundle.data['suppliers']
        
        bundle = super(SupplyResource, self).obj_update(bundle, **kwargs)
        
        for supplier_data in suppliers:
            supplier = Supplier.objects.get(pk=supplier_data['id'])
            try:
                product = Product.objects.get(supplier=supplier,
                                              supply=bundle.obj)
            except Product.DoesNotExist as e:
                product = Product(supplier=supplier,
                                  supply=bundle.obj)
            product = self.hydrate_product(product, bundle=bundle, **supplier_data)
            product.save()
            
        return bundle
    
    def hydrate_product(self, product=None, supply=None, supplier=None, bundle=None, **kwargs):
        """
        Takes the products and hydrates it with the appropriate variables
        """
        #Get product by supplier and supply if not provided
        if not product:
            product = Product.objects.get(supply=supply, supplier=supply)
            
        #Update all fields with value
        for field in product._meta.get_all_field_names():
            if field in kwargs and field not in ['id', 'supplier', 'supply']:
                if field.lower() == 'cost':
                    if bundle.request.user.has_perm('supplies.view_cost'):
                        product.cost = kwargs[field]
                else:
                    setattr(product, field, kwargs[field])
            
        return product
            
    def create_product(self, supply, supplier, cost, upc=None):
        """
        Creates a product
        """
        if not isinstance(supply, Supply) and isinstance(supply, dict):
            supply = Supply.objects.get(pk=supply['id'])
        
        if not isinstance(supplier, Supplier) and isinstance(supplier, dict):
            supplier = Supplier.objects.get(pk=supplier['id'])
        
        product = Product(supply=supply, supplier=supplier, cost=cost, upc=upc)
        product.save()
        return product
        
    def process_image(self, request, **kwargs):
        """
        Receives an image and processes it
        """
        filename = save_upload(request)
        
        image = S3Object.create(filename,
                        "supply/image/{0}.jpg".format(time.time()),
                        "media.dellarobbiathailand.com")
        #set Url, key and bucket
        data = {'url': image.generate_url(),
                "id": image.id,
                'key': image.key,
                'bucket': image.bucket}
        
        return self.create_response(request, data)

    
    def add(self, request, **kwargs):
        """
        Adds a quantity to the supply
        
        This method checks that the request method is post, and that
        there is both a quantity and an acknowledgement ID
        """
        if not request.method == "POST":
            pass#return self.create
        obj = self._meta.queryset.get(pk=kwargs['pk'])
        quantity = request.REQUEST.get('quantity')
        obj.quantity = round(float(obj.quantity) + float(quantity), 2)
        obj.save()
        
        #log the event
        log = Log(supply=obj,
                  message="Added {0}{1} of {2}".format(quantity, obj.units, obj.description),
                  action="ADD",
                  quantity=quantity)
        log.save()
        
        #Prepare a dictionary of the resource
        data = {}
        for key in obj.__dict__:
            if key[0] != "_":
                data[key] = obj.__dict__[key]
        
        """  
        data['supplier'] = {'name': obj.supplier.name,
                            'currency': obj.supplier.currency}"""
        return self.create_response(request, data)
    
    def subtract(self, request, **kwargs):
        """
        Subtracts a quantity to the supply
        
        This method checks that the request method is post, and that
        there is both a quantity and an acknowledgement ID
        """
        
        if not request.method == "POST":
            pass#return self.create
        obj = self._meta.queryset.get(pk=kwargs['pk'])
        quantity = request.REQUEST.get('quantity')
        obj.quantity = round(float(obj.quantity) - float(quantity), 2)
        obj.save()
        
        #log the event
        log = Log(supply=obj,
                  message="Subtracted {0}{1} of {2}".format(quantity, obj.units, obj.description),
                  action="SUBTRACT",
                  quantity=quantity)
        log.save()
        
        data = {}
        for key in obj.__dict__:
            if key[0] != "_":
                data[key] = obj.__dict__[key]
        """        
        data['supplier'] = {'name': obj.supplier.name,
                            'currency': obj.supplier.currency}"""
        return self.create_response(request, data)
    
    def type(self, request, **kwargs):
        data = [s for s in Supply.objects.values_list('type', flat=True).distinct()]
        return self.create_response(request, data)
    
    def dehydrate_image(self, bundle):
        """
        Takes an intance of a S3 Image
        and changes it to a dictionary of
        information and returns the bundle
        """
        if bundle.obj.image:
            return {'id': bundle.obj.image.id,
                    'url': bundle.obj.image.generate_url()}
        else:
            return None
    
    def dehydrate_supplier(self, bundle, supplier):
        """
        Takes the supplier bundle, and retrivies the product. 
        The cost, upc and reference is then combined with the
        supplier data bundle
        """
        product = Product.objects.get(supplier=supplier,
                                      supply=bundle.obj)
        data = {'upc': product.upc,
                'reference': product.reference,
                'admin_only': product.admin_only,
                'id': supplier.id,
                'purchasing_units': product.purchasing_units,
                'name': supplier.name}
        if bundle.request.user.has_perm('supplies.view_cost'):
            data['cost'] = product.cost
            
        return data
            
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
            obj_list = obj_list.filter(Q(product__supplier__name__icontains=query) | 
                                       Q(description__icontains=query) |
                                       Q(pattern__icontains=query) |
                                       Q(color__icontains=query))
        return obj_list
    
    def dehydrate(self, bundle):
        """
        Prepare the bundle for return to the client
        """
        bundle = super(FabricResource, self).dehydrate(bundle)
        if "suppliers" in bundle.data:
            bundle.data['supplier'] = bundle.data['suppliers'][0]

        try:
            bundle.data.update({'cost': bundle.data['supplier']['cost']})
        except KeyError:
            pass
        
        try:
            bundle.data.update({'purchasing_units': bundle.data['supplier']['purchasing_units']})
        except KeyError:
            pass
        
        del bundle.data['suppliers']
        
        return bundle

    
    
    
    
    
