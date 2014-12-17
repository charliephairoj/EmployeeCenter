"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import copy
from decimal import Decimal
import logging
import random
import unittest

from django.contrib.auth.models import User, Permission, ContentType
from rest_framework.test import APITestCase

from contacts.models import Supplier
from supplies.models import Supply, Fabric, Foam, Log, Product
from auth.models import S3Object


logger = logging.getLogger(__name__)

base_supplier = {"name": "Test Supplier",
                 "currency": "USD"}
base_address = {"address": {"address1": "22471 Sunbroon",
                            "city": "Mission Viejo",
                            "territory": "CA",
                            "country": "USA",
                            "zipcode": "92839"}}

base_supply = {"description": "test",
               'type': 'wood',
               "width": 100,
               "depth": 200,
               "height": 300,
               "width_units": 'in',
               "depth_units": 'in',
               "height_units": 'mm',
               "units": "ml",
               "notes": 'This is awesome',
               'width_units': 'm',
               'height_units': 'yd',
               "reference": "A2234",
               "cost": 100,
               "quantity": 10.8,
               "supplier": {"id": 1}}

base_fabric = base_supply.copy()
base_fabric.update({"pattern": "Max",
                    "color": "Hot Pink"})
base_fabric['purchasing_units'] = 'm'
base_fabric['type'] = 'fabric'
del base_fabric['depth']



def create_user(block_permissions=[]):
    """
    Creates a user
    """
    user = User.objects.create_user('test{0}'.format(random.randint(1, 100000)), 'test', 'test')
    user
    user.is_staff = True
    user.save()

    #Add permissions
    for p in Permission.objects.all():
        if p.codename not in block_permissions:
            user.user_permissions.add(p)
    return user
                
class SupplyAPITestCase(APITestCase):
    def setUp(self):
        """
        Set up the view 
        
        -login the user
        """
        super(SupplyAPITestCase, self).setUp()
        
        self.create_user()
        self.client.login(username='test', password='test')
        
        self.supplier = Supplier(**base_supplier)
        self.supplier.save()
        self.supplier2 = Supplier.objects.create(**base_supplier)
        self.supply = Supply.create(**base_supply)
        self.assertIsNotNone(self.supply.pk)
        self.supply2 = Supply.create(**base_supply)
        self.assertIsNotNone(self.supply2.pk)
        
        self.product = Product(supplier=self.supplier, supply=self.supply)
        self.product.save()
        
    def create_user(self):
        self.user = User.objects.create_user('test', 'test@yahoo.com', 'test')
        self.ct = ContentType(app_label='supplies')
        self.ct.save()
        self._create_and_add_permission('view_cost', self.user)
        self._create_and_add_permission('change_supply', self.user)
        self._create_and_add_permission('add_supply', self.user)
        self._create_and_add_permission('add_quantity', self.user)
        self._create_and_add_permission('subtract_quantity', self.user)
       
        
    def _create_and_add_permission(self, codename, user):
        p = Permission(content_type=self.ct, codename=codename)
        p.save()
        user.user_permissions.add(p)
        
    def test_get_list(self):
        """
        Tests that a standard get call works.
        """
        
        #Testing standard GET
        resp = self.client.get('/api/v1/supply/')
        self.assertEqual(resp.status_code, 200)
        
        #Tests the returned data
        resp_obj = resp.data
        self.assertIn('results', resp_obj)
        self.assertEqual(len(resp_obj['results']), 2)
    
    def test_get(self):
        """
        Tests getting a supply that doesn't have the price 
        where the user is not authorized to view the price
        """
        resp = self.client.get('/api/v1/supply/1/')
        self.assertEqual(resp.status_code, 200)
        
        obj = resp.data
        #self.assertEqual(Decimal(obj['cost']), Decimal('100'))
        self.assertIn('description', obj)
        self.assertEqual(obj['description'], 'test')
        self.assertIn('type', obj)
        self.assertEqual(obj['type'], 'wood')
        

        resp = self.client.get('/api/v1/supply/1/?country=TH')
        self.assertEqual(resp.status_code, 200)
        obj = resp.data
        self.assertEqual(obj['quantity'], 10.8)
        self.assertIn('suppliers', obj)
        self.assertEqual(len(obj['suppliers']), 1)
        supplier = obj['suppliers'][0]
    
    def test_get_log(self):
        """
        Tests gettings the log for all the supplies
        """
        
        resp = self.client.get('/api/v1/supply/log/')
        #self.assertEqual(resp.status_code, 200)
        obj = resp.data
        #self.assertIsInstance(obj, list)
    
    def test_get_without_price(self):
        """
        Tests getting a supply that doesn't have the price 
        where the user is not authorized to view the price
        """
        #Delete the view cost permission from the user
        self.user.user_permissions.remove(Permission.objects.get(codename='view_cost', content_type=self.ct))
        
        #tests the response
        resp = self.client.get('/api/v1/supply/1/')
        self.assertEqual(resp.status_code, 200)
        
        #Tests the data returned
        obj = resp.data
        self.assertNotIn("cost", obj)
    
    def test_get_types(self):
        """
        Tests getting the different types
        used to describe supplies
        """
        resp = self.client.get('/api/v1/supply/type/')
        #self.assertEqual(resp.status_code, 200)
        type_list = resp.data
        #self.assertIn('wood', type_list)
        
    def test_post_single_supplier(self):
        """
        Tests posting to the server
        """
        #Test creating an objects. 
        self.assertEqual(Supply.objects.count(), 2)
        resp = self.client.post('/api/v1/supply/', format='json',
                                    data=base_supply)
        self.assertEqual(resp.status_code, 201, msg=resp)

        #Tests the dat aturned
        obj = resp.data
        self.assertEqual(obj['id'], 3)
        self.assertEqual(obj['width'], '100.00')
        self.assertEqual(obj['depth'], '200.00')
        self.assertEqual(obj['height'], '300.00')
        self.assertEqual(obj['description'], 'test')
        self.assertEqual(obj['height_units'], 'yd')
        self.assertEqual(obj['width_units'], 'm')
        self.assertEqual(obj['notes'], 'This is awesome')
        self.assertIn('type', obj)
        self.assertEqual(obj['type'], 'wood')
        self.assertIn('suppliers', obj)
        self.assertEqual(len(obj['suppliers']), 1)
        
        #Test Supplier
        supplier = obj['suppliers'][0]
        self.assertEqual(supplier['reference'], 'A2234')
        self.assertEqual(supplier['cost'], Decimal('100'))
        
        #TEsts the object created
        supply = Supply.objects.order_by('-id').all()[0]
        supply.supplier = supply.suppliers.all()[0]
        self.assertEqual(supply.id, 3)
        self.assertEqual(supply.width, 100)
        self.assertEqual(supply.depth, 200)
        self.assertEqual(supply.height, 300)
        #self.assertEqual(supply.reference, 'A2234')
        self.assertEqual(supply.description, 'test')
        #self.assertEqual(supply.cost, 100)
        self.assertEqual(supply.height_units, 'yd')
        self.assertEqual(supply.width_units, 'm')
        self.assertEqual(supply.notes, 'This is awesome')
        self.assertIsNotNone(supply.type)
        self.assertEqual(supply.type, 'wood')
        self.assertIsNotNone(supply.suppliers)
        self.assertEqual(supply.suppliers.count(), 1)

    def test_posting_with_custom_type(self):
        """
        Testing creating a new resource via POST 
        that has a custom type
        """
        #Testing returned types pre POST
        resp0 = self.client.get('/api/v1/supply/type/', format='json')
        self.assertEqual(resp0.status_code, 200, msg=resp0)
        type_list = resp0.data
        self.assertNotIn('egg', type_list)
        self.assertIn('wood', type_list)
        self.assertEqual(len(type_list), 1)
        
        #POST
        modified_supply = base_supply.copy()
        modified_supply['type'] = 'egg'
        resp = self.client.post('/api/v1/supply/', format='json',
                                    data=modified_supply)
        self.assertEqual(resp.status_code, 201)
        
        #Tests the response
        obj = resp.data
        self.assertIn('type', obj)
        self.assertNotIn('custom-type', obj)
        self.assertEqual(obj['type'], 'egg')
        
        """
        resp2 = self.client.get('/api/v1/supply/type/', format='json')
        self.assertHttpOK(resp2)
        type_list = self.deserialize(resp2)
        self.assertIn('egg', type_list)
        self.assertIn('wood', type_list)
        self.assertEqual(len(type_list), 2)
        """
        
    def test_put(self):
        """
        Tests adding quantity to the item
        """
        
        #Validate original data
        supply = Supply.objects.get(pk=1)
        supply.country = 'TH'
        self.assertEqual(supply.quantity, 10.8)
        self.assertEqual(Log.objects.all().count(), 0)
        
        #Prepare modified data for PUT
        modified_data = base_supply.copy()
        modified_data['description'] = 'new'
        modified_data['type'] = 'Glue'
        modified_data['quantity'] = '11'
        
        #Tests the api and the response
        self.assertEqual(Supply.objects.count(), 2)
        resp = self.client.put('/api/v1/supply/1/?country=TH', format='json',
                                   data=modified_data)
        
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Supply.objects.count(), 2)

        #Tests the returned data
        obj = resp.data
        self.assertEqual(obj['type'], 'Glue')
        self.assertEqual(float(obj['quantity']), 11)
        self.assertEqual(obj['description'], 'new')
        self.assertFalse(obj.has_key('quantity_th'))
        self.assertFalse(obj.has_key('quantity_kh'))
        
        #Tests the resource in the database
        supply = Supply.objects.get(pk=1)
        supply.country = 'TH'
        self.assertEqual(supply.type, 'Glue')
        self.assertEqual(supply.country, 'TH')
        self.assertEqual(supply.description, 'new')
        self.assertEqual(supply.quantity, 11)
        self.assertEqual(Log.objects.all().count(), 1)
        log = Log.objects.all()[0]
        self.assertEqual(log.action, 'ADD')
        self.assertEqual(log.quantity, Decimal('0.2'))
        self.assertEqual(log.message, "Added 0.2ml to new")
        
    def test_put_without_quantity_change(self):
        """
        Tests adding quantity to the item
        """
        
        #Validate original data
        supply = Supply.objects.get(pk=1)
        supply.country = 'TH'
        self.assertEqual(supply.quantity, 10.8)
        self.assertEqual(Log.objects.all().count(), 0)
        
        #Prepare modified data for PUT
        modified_data = base_supply.copy()
        modified_data['description'] = 'new'
        modified_data['type'] = 'Glue'
        modified_data['quantity'] = '10.8'
        modified_data['width_units'] = 'cm'
        modified_data['depth_units'] = 'cm'
        
        #Tests the api and the response
        self.assertEqual(Supply.objects.count(), 2)
        resp = self.client.put('/api/v1/supply/1/?country=TH', format='json',
                                   data=modified_data)
        
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Supply.objects.count(), 2)

        #Tests the returned data
        obj = resp.data
        self.assertEqual(obj['type'], 'Glue')
        self.assertEqual(float(obj['quantity']), 10.8)
        self.assertEqual(obj['description'], 'new')
        self.assertEqual(obj['width_units'], 'cm')
        self.assertEqual(obj['depth_units'], 'cm')
        self.assertFalse(obj.has_key('quantity_th'))
        self.assertFalse(obj.has_key('quantity_kh'))
        
        #Tests the resource in the database
        supply = Supply.objects.get(pk=1)
        supply.country = 'TH'
        self.assertEqual(supply.type, 'Glue')
        self.assertEqual(supply.country, 'TH')
        self.assertEqual(supply.description, 'new')
        self.assertEqual(supply.quantity, 10.8)
        
        self.assertEqual(Log.objects.all().count(), 0)
        
    def test_put_subtracting_quantity_to_0(self):
        """
        Tests adding quantity to the item
        """
        
        #Validate original data
        supply = Supply.objects.get(pk=1)
        supply.country = 'TH'
        supply.quantity = 1
        supply.save()
        
        self.assertEqual(supply.quantity, 1)
        self.assertEqual(Log.objects.all().count(), 0)
        
        #Prepare modified data for PUT
        modified_data = base_supply.copy()
        modified_data['description'] = 'new'
        modified_data['type'] = 'Glue'
        modified_data['quantity'] = '0'
        
        #Tests the api and the response
        self.assertEqual(Supply.objects.count(), 2)
        resp = self.client.put('/api/v1/supply/1/?country=TH', format='json',
                                   data=modified_data)
        
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Supply.objects.count(), 2)

        #Tests the returned data
        obj = resp.data
        self.assertEqual(obj['quantity'], 0)

        self.assertFalse(obj.has_key('quantity_th'))
        self.assertFalse(obj.has_key('quantity_kh'))
        
        #Tests the resource in the database
        supply = Supply.objects.get(pk=1)
        supply.country = 'TH'
        self.assertEqual(supply.quantity, 0)
        
        log = Log.objects.all().order_by('-id')[0]
        self.assertEqual(Log.objects.all().count(), 1)
        self.assertEqual(log.quantity, 1)
        self.assertEqual(log.action, 'SUBTRACT')
        
    @unittest.skip('Not yet implemented')    
    def test_add(self):
        """
        Tests adding a quantity
        to the specific url
        """
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('10.8'))
        resp = self.client.post('/api/v1/supply/1/add/?quantity=5', format='json')
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('15.8'))
        
    @unittest.skip('Not yet implemented')    
    def test_subract(self):
        """
        Tests adding a quantity
        to the specific url
        """
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('10.8'))
        resp = self.client.post('/api/v1/supply/1/subtract/?quantity=5', format='json')
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('5.8'))
        
    def test_put_add_quantity(self):
        """
        Tests adding quantity to the item
        """
        modified_data = base_supply.copy()
        modified_data['quantity'] = '14'
        modified_data['description'] = 'new'
        
        #Tests the api and the response
        self.assertEqual(Supply.objects.count(), 2)
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('10.8'))
        resp = self.client.put('/api/v1/supply/1/', format='json',
                                   data=modified_data)
        
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Supply.objects.count(), 2)
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('14'))
        self.assertEqual(Supply.objects.get(pk=1).description, 'new')

        #Tests the returned data
        obj = resp.data
        self.assertEqual(float(obj['quantity']), float('14'))
    
    def test_put_subtract_quantity(self):
        """
        Tests adding quantity to the item
        """
        modified_data = base_supply.copy()
        modified_data['quantity'] = '8'
        
        #Tests the api and the response
        self.assertEqual(Supply.objects.count(), 2)
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('10.8'))
        resp = self.client.put('/api/v1/supply/1/', format='json',
                                   data=modified_data)
        
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Supply.objects.count(), 2)
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('8'))

        #Tests the returned data
        obj = resp.data
        self.assertEqual(float(obj['quantity']), float('8'))
        
    def test_put_to_create_new_product(self):
        """
        Tests adding a new supplier/product to the supply
        """
        logger.debug("\n\nTest creating a new supply/product via PUT\n")
        modified_data = copy.deepcopy(base_supply)
        modified_data['suppliers'] = [{'id': 1,
                                       'supplier': {'id': 1}},
                                      {'reference': 'A4',
                                        'cost': '19.99',
                                        'purchasing_units': 'ml',
                                        'quantity_per_purchasing_unit': 4,
                                        'supplier': {'id': 2}}]
                                        
        resp = self.client.put('/api/v1/supply/1/', format='json', data=modified_data)
        
        self.assertEqual(resp.status_code, 200, msg=resp)
        self.assertEqual(Supply.objects.count(), 2)
        
        obj = resp.data
        self.assertIn('suppliers', obj)
        self.assertEqual(len(obj['suppliers']), 2)
        
class FabricAPITestCase(APITestCase):
    
    def setUp(self):
        """
        Set up the view 
        
        -login the user
        """
        super(FabricAPITestCase, self).setUp()
        
        self.create_user()
        self.client.login(username='test', password='test')
        
        self.supplier = Supplier(**base_supplier)
        self.supplier.save()
        self.supply = Fabric.create(**base_fabric)
        self.assertIsNotNone(self.supply.pk)
        self.supply2 = Fabric.create(**base_fabric)
        self.assertIsNotNone(self.supply.pk)
        
        self.product = Product(supplier=self.supplier, supply=self.supply)
        self.product.save()
    
    def create_user(self):
        self.user = User.objects.create_user('test', 'test@yahoo.com', 'test')
        self.ct = ContentType(app_label='supplies')
        self.ct.save()
        self._create_and_add_permission('view_cost', self.user)
        self._create_and_add_permission('change_fabric', self.user)
        self._create_and_add_permission('add_fabric', self.user)
        self._create_and_add_permission('add_quantity', self.user)
        self._create_and_add_permission('subtract_quantity', self.user)
        
    def _create_and_add_permission(self, codename, user):
        p = Permission(content_type=self.ct, codename=codename)
        p.save()
        user.user_permissions.add(p)
        
    def _remove_permission(self, codename):
        self.user.user_permissions.remove(Permission.objects.get(codename=codename, content_type=self.ct))
        
    def test_get_list(self):
        """
        Tests that a standard get call works.
        """
        
        #Testing standard GET
        resp = self.client.get('/api/v1/fabric/')
        self.assertEqual(resp.status_code, 200)
        
        #Tests the returned data
        resp_obj = resp.data
        self.assertIn('results', resp_obj)
        self.assertEqual(len(resp_obj['results']), 2)
    
    def test_get(self):
        """
        Tests getting a supply that doesn't have the price 
        where the user is not authorized to view the price
        """
        resp = self.client.get('/api/v1/fabric/1/')
        self.assertEqual(resp.status_code, 200)
        
        obj = resp.data
        #self.assertEqual(float(obj['cost']), float('100'))
        
    def test_get_without_price(self):
        """
        Tests getting a supply that doesn't have the price 
        where the user is not authorized to view the price
        """
        #Delete the view cost permission from the user
        self.user.user_permissions.remove(Permission.objects.get(codename='view_cost', content_type=self.ct))
        
        #tests the response
        resp = self.client.get('/api/v1/fabric/1/')
        self.assertEqual(resp.status_code, 200)
        
        #Tests the data returned
        obj = resp.data
        self.assertNotIn("cost", obj)
        
    def test_post(self):
        """
        Tests posting to the server
        """
        #Test creating an objects. 
        self.assertEqual(Supply.objects.count(), 2)
        resp = self.client.post('/api/v1/fabric/', format='json',
                                    data=base_fabric)
        self.assertEqual(resp.status_code, 201, msg=resp)
       
        #Tests the dat aturned
        obj = resp.data
        self.assertEqual(obj['id'], 3)
        self.assertEqual(obj['width'], '100.00')
        self.assertEqual(obj['depth'], '0.00')
        self.assertEqual(obj['height'], '300.00')
        self.assertEqual(obj['description'], 'test')
        self.assertNotIn('reference', obj)
        self.assertNotIn('cost', obj)
        self.assertIn('suppliers', obj)
        
        supplier = obj['suppliers'][0]
        self.assertEqual(supplier['reference'], 'A2234')
        self.assertEqual(int(supplier['cost']), 100)
        
    def test_put(self):
        """
        Tests adding quantity to the item
        """
        modified_data = base_supply.copy()
        modified_data['cost'] = '111'
        modified_data['color'] = 'Aqua'
        modified_data['pattern'] = 'Stripes'
        #Tests the api and the response
        self.assertEqual(Supply.objects.count(), 2)
        resp = self.client.put('/api/v1/fabric/1/', format='json',
                                   data=modified_data)
        
        self.assertEqual(resp.status_code, 200, msg=resp)
        self.assertEqual(Supply.objects.count(), 2)

        #Tests the returned data
        obj = resp.data
        self.assertEqual(obj['color'], 'Aqua')
        self.assertEqual(obj['pattern'], 'Stripes')
        
    def test_put_add_quantity(self):
        """
        Tests adding quantity to the item
        """
        modified_data = base_supply.copy()
        modified_data['quantity'] = '14'
        modified_data['color'] = 'Aqua'
        modified_data['pattern'] = 'Stripes'

        #Tests the api and the response
        self.assertEqual(Supply.objects.count(), 2)
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('10.8'))
        resp = self.client.put('/api/v1/fabric/1/', format='json',
                                   data=modified_data)
        self.assertEqual(resp.status_code, 200, msg=resp)
        self.assertEqual(Supply.objects.count(), 2)
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('14'))

        #Tests the returned data
        obj = resp.data
        self.assertEqual(float(obj['quantity']), float('14'))
        
    def test_put_subtract_quantity(self):
        """
        Tests adding quantity to the item
        """
        modified_data = base_supply.copy()
        modified_data['quantity'] = '8'
        modified_data['color'] = 'Aqua'
        modified_data['pattern'] = 'Stripes'

        #Tests the api and the response
        self.assertEqual(Supply.objects.count(), 2)
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('10.8'))
        resp = self.client.put('/api/v1/fabric/1/', format='json',
                                   data=modified_data)
        
        self.assertEqual(resp.status_code, 200, msg=resp)
        self.assertEqual(Supply.objects.count(), 2)
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('8'))

        #Tests the returned data
        obj = resp.data
        self.assertEqual(float(obj['quantity']), float('8'))
      
    @unittest.skip('ok')  
    def test_put_add_quantity_fail(self):
        """
        Tests an unauthorized addition of quantity
        """
        #Delete permissions
        self._remove_permission("add_quantity")
        
        #Create new data
        modified_data = base_fabric.copy()
        modified_data['quantity'] = '20'
        
        #Tests the api and response
        resp = self.client.put('/api/v1/fabric/1/', format='json',
                                   data=modified_data)
        self.assertEqual(Fabric.objects.get(pk=1).quantity, float('10.8'))
        #Tests the data retured
        obj = resp.data
        self.assertEqual(float(obj['quantity']), float('10.8'))
        
    @unittest.skip('ok')
    def test_put_subtract_quantity_fail(self):
        """
        Tests an unauthorized addition of quantity
        """
        #Delete permissions
        self._remove_permission("subtract_quantity")
        
        #Create new data
        modified_data = base_fabric.copy()
        modified_data['quantity'] = '6'
        
        #Tests the api and response
        resp = self.client.put('/api/v1/fabric/1/', format='json',
                                   data=modified_data)
        self.assertEqual(Fabric.objects.get(pk=1).quantity, float('10.8'))
        #Tests the data retured
        obj = resp.data
        self.assertEqual(float(obj['quantity']), float('10.8'))
        