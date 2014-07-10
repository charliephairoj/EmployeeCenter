"""
API file for supplies
"""
from decimal import Decimal
from datetime import datetime, timedelta
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
from tastypie.constants import ALL, ALL_WITH_RELATIONS

from supplies.models import Supply, Fabric, Product, Log
from contacts.models import Supplier
from supplies.validation import SupplyValidation, FabricValidation
from utilities.http import save_upload
from auth.models import S3Object
from media.stickers import StickerPage


logger = logging.getLogger(__name__)


class SupplyResource(ModelResource):
    log = fields.ToManyField('supplies.api.LogResource', 'log') 
    
    class Meta:
        queryset = Supply.objects.all()
        resource_name = 'supply'
        always_return_data = True
        validation = SupplyValidation()
        authorization = DjangoAuthorization()
        ordering = ['image']
        excludes = ['quantity_th', 'quantity_kh']
        filtering = {'id': ALL,
                     'upc': 'exact',
                     'quantity': ALL,
                     'last_modified': ALL}
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
                url(r"^{0}/log$".format(self._meta.resource_name), self.wrap_view('log')),
                url(r"^{0}/(?P<pk>\d+)/subtract".format(self._meta.resource_name), self.wrap_view('subtract')),
                url(r"^{0}/(?P<pk>\d+)/add$".format(self._meta.resource_name), self.wrap_view('add')),
                
                ]
        
    def hydrate(self, bundle):
        """
        Implements the hydrate function 
        """
        #Set the country, in order to retrieve the correct quantity
        bundle = self._set_country(bundle)
            
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
            
        #Adds the quantity
        try:
            if Decimal(str(bundle.obj.quantity)) != Decimal(bundle.data['quantity']) and bundle.obj.quantity:
                action = "ADD" if float(bundle.data['quantity']) > bundle.obj.quantity else "SUBTRACT"
                diff = abs(Decimal(str(bundle.obj.quantity)) - Decimal(bundle.data['quantity']))
                bundle.obj.quantity = float(bundle.data['quantity'])
                log = Log(supply=bundle.obj,
                          action=action,
                          quantity=diff,
                          message=u"{0}ed {1}{2} {3} {4}".format(action.capitalize(),
                                                               diff,
                                                               bundle.obj.units,
                                                               "to" if action == "ADD" else "from",
                                                               bundle.obj.description))
                log.save()
           
        except KeyError:
            pass
            
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
        #Checks if the country is set
        bundle = self._set_country(bundle)
           
        #Adds the quantity to the data field
        bundle.data['quantity'] = bundle.obj.quantity
             
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
        
            log = Log(supply=product.supply,
                      supplier=product.supplier,
                      action="PRICE CHANGE",
                      quantity=None,
                      cost=product.cost,
                      message=u"Price set to {0}{1} for {2} [Supplier: {3}]".format(product.cost,
                                                                                   product.supplier.currency,
                                                                                   product.supply.description,
                                                                                   product.supplier.name))
            log.save()
            
        return bundle
    
    def obj_update(self, bundle, **kwargs):
        """
        Updates the supply, the product relationship witht the supplier
        
        Extra suppliers before the parent obj_update method destroys it.
        """
        #Get suppliers data before erased by parent method
        try:
            suppliers = bundle.data['suppliers']
        except KeyError as e:
            try: 
                suppliers = [bundle.data['supplier']]
            except KeyError:
                raise
        
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
            product = Product.objects.get(supply=supply, supplier=supplier)
            
        #Update all fields with value
        for field in product._meta.get_all_field_names():
            if field in kwargs and field not in ['id', 'supplier', 'supply']:
                if field.lower() == 'cost':
                    if bundle.request.user.has_perm('supplies.view_cost'):
                        if Decimal(kwargs[field]) != product.cost:
                            old_price = product.cost
                            product.cost = kwargs[field]
                            log = Log(supply=product.supply,
                                      supplier=product.supplier,
                                      action="PRICE CHANGE",
                                      quantity=None,
                                      cost=product.cost,
                                      message=u"Price change from {0}{2} to {1}{2} for {3} [Supplier: {4}]".format(old_price,
                                                                                                                  product.cost,
                                                                                                                  product.supplier.currency,
                                                                                                                  product.supply.description,
                                                                                                                  product.supplier.name))
                            log.save()
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
  
        obj = self._meta.queryset.get(pk=kwargs['pk'])
        if request.GET.has_key('country'):
            obj.country = request.GET.get('country')
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
        data = {'quantity': obj.quantity}
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
        
       
        obj = self._meta.queryset.get(pk=kwargs['pk'])
        if request.GET.has_key('country'):
            obj.country = request.GET.get('country')
        quantity = request.REQUEST.get('quantity')
        obj.quantity = round(float(obj.quantity) - float(quantity), 2)
        obj.save()
        
        #log the event
        log = Log(supply=obj,
                  message="Subtracted {0}{1} of {2}".format(quantity, obj.units, obj.description),
                  action="SUBTRACT",
                  quantity=quantity)
        log.save()
        
        data = {'quantity': obj.quantity}
        for key in obj.__dict__:
            if key[0] != "_":
                data[key] = obj.__dict__[key]
        """        
        data['supplier'] = {'name': obj.supplier.name,
                            'currency': obj.supplier.currency}"""
        return self.create_response(request, data)
    
    def type(self, request, **kwargs):
        """
        returns all the types that have been used for supplies
        """
        data = [s for s in Supply.objects.values_list('type', flat=True).distinct()]
        return self.create_response(request, data)
        
    def log(self, request, **kwargs):
        """
        returns all the logs for supplies checkout in the last two weeks
        """
        start_date = datetime.today() - timedelta(days=7)
        end_date = datetime.today() + timedelta(days=1)
        
        logs = Log.objects.filter(timestamp__range=[start_date, end_date])
        data = [self.dehydrate_log(log) for log in logs]
        
        return self.create_response(request, data)
        
    def dehydrate_log(self, log):
        """
        Takes a log instance and returns
        a dictionary of its properties
        """
        try:
            log_dict = {'id': log.id,
                        'message': log.message,
                        'quantity': log.quantity,
                        'action': log.action,
                        'timestamp': log.timestamp.strftime('%B %d, %Y %H:%M'),
                        'supply': {
                            'id': log.supply.id,
                            'description': log.supply.description
                        }}
                        
            return log_dict
        except AttributeError as e:
            logger.warn(e)
            
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

    def _set_country(self, bundle):
        """
        Sets the country for the supply object
        
        The supply object uses the country to correct determine the which
        quantity to return for the quantity property. By default, the 
        country is Thailand.
        """
        if bundle.request.GET.has_key('country'):
            bundle.obj.country = bundle.request.GET.get('country')
        else:
            bundle.obj.country = 'TH'
            
        return bundle
    
class LogResource(ModelResource):
    supply = fields.ForeignKey('supplies.api.SupplyResource', 'supply')
    supplier = fields.ForeignKey('contacts.api.SupplierResource', 'supplier', null=True)
    
    class Meta:
        queryset = Log.objects.all().order_by('-id')  
        resource_name = 'log'
        #ordering = ['quantity']
        filtering = {
            'supply': ALL_WITH_RELATIONS,
            'supplier': ALL_WITH_RELATIONS,
            'timestamp': ALL,
            'action': ALL
        }
        
        
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
    
    def hydrate(self, bundle):
        """
        Prepare the fabric to be saved to the database
        """
        bundle.obj.description = "Pattern:{0}, Col: {1}".format(bundle.data['pattern'], bundle.data['color'])
        bundle.obj.type = "Fabric"
        bundle.obj.units = 'm'
        
        if "cost" in bundle.data:
            if float(bundle.data['cost']) > 0:
                try:
                    try: 
                        p = Product.objects.get(supply=bundle.obj,
                                                supplier=Supplier.objects.get(pk=bundle.data['supplier']['id']))
                    except Product.DoesNotExist:
                        p = Product()
                        p.supply = bundle.obj
                        p.supplier = Supplier.objects.get(pk=bundle.data['supplier']['id'])
                        p.cost = bundle.data['cost']
                    p.save()
                except KeyError:
                    pass
        
        return bundle
        
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

    
    
    
    
    
