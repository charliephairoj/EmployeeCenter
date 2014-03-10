"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from decimal import Decimal
import logging
import random
import unittest

from django.contrib.auth.models import User, Permission, ContentType
from tastypie.test import ResourceTestCase

from contacts.models import Supplier
from supplies.models import Supply, Fabric, Foam, SupplyLog, Product
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
               "units": "ml",
               "notes": 'This is awesome',
               'width_units': 'm',
               'height_units': 'yd',
               "quantity": 10.8,
               "suppliers": [{"id": 1,
                              'cost': 100,
                              'reference': 'A2234',
                              'purchasing_units': 'yd'}]}

base_supply_with_id = {'id': 1, 
                       'cost': 120,
                       'upc': '123456',
                       'type': 'wood',
                       'width': 100,
                       'depth': 200,
                       'height': 300,
                       'units': 'ml',
                       'quantity': 10.8,
                       'notes': 'This is awesome',
                       'suppliers': [{'id': 2, 
                                      'purchasing_units': 'yd',
                                      'cost': 120}]}

base_fabric = base_supply.copy()
base_fabric['supplier'] = base_fabric['suppliers'][0]
del base_fabric['suppliers']
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
                
class SupplyResourceTestCase(ResourceTestCase):
    def setUp(self):
        """
        Set up the view 
        
        -login the user
        """
        super(SupplyResourceTestCase, self).setUp()
        
        self.create_user()
        self.api_client.client.login(username='test', password='test')
        
        self.supplier = Supplier(**base_supplier)
        self.supplier.save()
        self.supplier2 = Supplier(**base_supplier)
        self.supplier2.save()
        self.supply = Supply.create(**base_supply)
        self.assertIsNotNone(self.supply.pk)
        self.product = Product(supplier=self.supplier, 
                               supply=self.supply,
                               cost=base_supply['suppliers'][0]['cost'],
                               reference=base_supply['suppliers'][0]['reference'],
                               purchasing_units=base_supply['suppliers'][0]['purchasing_units'])
        self.product.save()
        self.supply2 = Supply.create(**base_supply)
        self.assertIsNotNone(self.supply.pk)
        
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
        resp = self.api_client.get('/api/v1/supply')
        self.assertHttpOK(resp)
        
        #Tests the returned data
        resp_obj = self.deserialize(resp)
        self.assertIn('objects', resp_obj)
        self.assertEqual(len(resp_obj['objects']), 2)
    
    def test_get_list_with_supplier_id(self):
        """
        Tests getting a filter list of supplies 
        """
        resp = self.api_client.get('/api/v1/supply?supplier_id=1')
        self.assertHttpOK(resp)
        
    def test_get(self):
        """
        Tests getting a supply that doesn't have the price 
        where the user is not authorized to view the price
        """
        resp = self.api_client.get('/api/v1/supply/1')
        self.assertHttpOK(resp)
        
        obj = self.deserialize(resp)
        self.assertIn('description', obj)
        self.assertEqual(obj['description'], 'test')
        self.assertIn('type', obj)
        self.assertEqual(obj['type'], 'wood')
        self.assertEqual(obj['units'], 'ml')
        self.assertIn('suppliers', obj)
        self.assertTrue(isinstance(obj['suppliers'], list), 'The suppliers should be a list')
        supplier = obj['suppliers'][0]
        self.assertEqual(supplier['id'], 1)
        self.assertEqual(int(supplier['cost']), 100)
        self.assertEqual(supplier['reference'], 'A2234')
        self.assertEqual(supplier['purchasing_units'], 'yd')
        #Tests that the sticker is in the data returned
        self.assertIn('sticker', obj, "There should be a sticker key in the data returned")
        self.assertIn('url', obj['sticker'], "There should be a url key in the data['sticker']")
        self.assertIsNotNone(obj['sticker']['url'], "The sticker's url should not be none")
        
        
    def test_get_without_price(self):
        """
        Tests getting a supply that doesn't have the price 
        where the user is not authorized to view the price
        """
        #Delete the view cost permission from the user
        self.user.user_permissions.remove(Permission.objects.get(codename='view_cost', content_type=self.ct))
        
        #tests the response
        resp = self.api_client.get('/api/v1/supply/1')
        self.assertHttpOK(resp)
        
        #Tests the data returned
        obj = self.deserialize(resp)
        supplier = obj['suppliers'][0]
        self.assertNotIn("cost", supplier)
    
    def test_get_types(self):
        """
        Tests getting the different types
        used to describe supplies
        """
        resp = self.api_client.get('/api/v1/supply/type')
        self.assertHttpOK(resp)
        type_list = self.deserialize(resp)
        self.assertIn('wood', type_list)
        
    def test_post_single_supplier(self):
        """
        Tests posting to the server
        """
        #Test creating an objects. 
        self.assertEqual(Supply.objects.count(), 2)
        resp = self.api_client.post('/api/v1/supply', format='json',
                                    data=base_supply)
        self.assertHttpCreated(resp)
       
        #Tests the dat aturned
        obj = self.deserialize(resp)
        self.assertEqual(obj['id'], 3)
        self.assertEqual(int(obj['width']), 100)
        self.assertEqual(int(obj['depth']), 200)
        self.assertEqual(int(obj['height']), 300)
        self.assertEqual(obj['description'], 'test')
        self.assertEqual(obj['height_units'], 'yd')
        self.assertEqual(obj['width_units'], 'm')
        self.assertEqual(obj['notes'], 'This is awesome')
        self.assertIn('type', obj)
        self.assertEqual(obj['type'], 'wood')
        #Tests supplier data
        self.assertIn('suppliers', obj)
        self.assertTrue(isinstance(obj['suppliers'], list))
        supplier = obj['suppliers'][0]
        self.assertEqual(supplier['id'], 1)
        self.assertEqual(supplier['cost'], '100')
        self.assertEqual(supplier['reference'], 'A2234')
        #TEsts the object created
        supply = Supply.objects.order_by('-id').all()[0]
        self.assertEqual(supply.id, 3)
        self.assertEqual(supply.width, 100)
        self.assertEqual(supply.depth, 200)
        self.assertEqual(supply.height, 300)
        self.assertEqual(supply.description, 'test')
        self.assertEqual(supply.height_units, 'yd')
        self.assertEqual(supply.width_units, 'm')
        self.assertEqual(supply.notes, 'This is awesome')
        self.assertIsNotNone(supply.type)
        self.assertEqual(supply.type, 'wood')
        self.assertIsNotNone(supply.suppliers)
        self.assertEqual(supply.suppliers.count(), 1)
        supplier = supply.suppliers.all()[0]
        self.assertEqual(supplier.id, 1)
        product = Product.objects.get(supplier=supplier, supply=supply)
        self.assertEqual(product.cost, 100)
        self.assertEqual(product.reference, 'A2234')
        
    def test_posting_with_supply_id(self):
        """
        Tests creating a new resource via POST where
        the supply is already created and has a new id
        """
        resp = self.api_client.post('/api/v1/supply/', data=base_supply_with_id, 
                                    format='json')
        self.assertHttpCreated(resp)
        
        #Verify response properties
        supply_obj = self.deserialize(resp)
        self.assertEqual(supply_obj['id'], 1, "The supply id should equal 1")
        self.assertIn('suppliers', supply_obj)
        self.assertTrue(isinstance(supply_obj['suppliers'], list), "Suppliers should be a list")
        self.assertEqual(supply_obj['type'], 'wood')
        self.assertEqual(supply_obj['width'], '100')
        self.assertEqual(supply_obj['depth'], '200')
        self.assertEqual(supply_obj['height'], '300')
        self.assertEqual(supply_obj['units'], 'ml')
        self.assertEqual(supply_obj['notes'], 'This is awesome')
        self.assertEqual(supply_obj['quantity'], 10.8)
        s_data = supply_obj['suppliers'][0]
        self.assertEqual(s_data['id'], 1)
        self.assertEqual(s_data['cost'], '100')
        self.assertEqual(s_data['reference'], 'A2234')
        self.assertEqual(s_data['purchasing_units'], 'yd')
        
    def test_posting_with_custom_type(self):
        """
        Testing creating a new resource via POST 
        that has a custom type
        """
        #Testing returned types pre POST
        resp0 = self.api_client.get('/api/v1/supply/type', format='json')
        self.assertHttpOK(resp0)
        type_list = self.deserialize(resp0)
        self.assertNotIn('egg', type_list)
        self.assertIn('wood', type_list)
        self.assertEqual(len(type_list), 1)
        
        #POST
        modified_supply = base_supply.copy()
        modified_supply['type'] = 'Custom'
        modified_supply['custom-type'] = 'egg'
        resp = self.api_client.post('/api/v1/supply', format='json',
                                    data=modified_supply)
        self.assertHttpCreated(resp)
        
        #Tests the response
        obj = self.deserialize(resp)
        self.assertIn('type', obj)
        self.assertNotIn('custom-type', obj)
        self.assertEqual(obj['type'], 'egg')
        
        resp2 = self.api_client.get('/api/v1/supply/type', format='json')
        self.assertHttpOK(resp2)
        type_list = self.deserialize(resp2)
        self.assertIn('egg', type_list)
        self.assertIn('wood', type_list)
        self.assertEqual(len(type_list), 2)
        
    def test_put(self):
        """
        Tests adding quantity to the item
        """
        modified_data = base_supply.copy()
        modified_data['description'] = 'new'
        modified_data['type'] = 'Glue'
        modified_data['suppliers'].append({'id':2, 
                                           'cost':110, 
                                           'upc':'1122', 
                                           'reference':'AHH',
                                           'purchasing_units': 'mm'})
        modified_data['suppliers'][0]['upc'] = 'testUPC'
        
        #Tests the api and the response
        self.assertEqual(Supply.objects.count(), 2)
        resp = self.api_client.put('/api/v1/supply/1', format='json',
                                   data=modified_data)
        
        self.assertHttpOK(resp)
        self.assertEqual(Supply.objects.count(), 2)

        #Tests the returned data
        obj = self.deserialize(resp)
        self.assertEqual(obj['type'], 'Glue')
        self.assertIn('suppliers', obj)
        self.assertTrue(isinstance(obj['suppliers'], list))
        self.assertEqual(len(obj['suppliers']), 2)
        supplier1 = obj['suppliers'][0]
        self.assertEqual(supplier1['id'], 1)
        self.assertEqual(supplier1['cost'], '100')
        self.assertEqual(supplier1['purchasing_units'], 'yd')
        self.assertEqual(supplier1['upc'], 'testUPC')
        supplier2 = obj['suppliers'][1]
        self.assertEqual(supplier2['id'], 2)
        self.assertEqual(supplier2['cost'], '110')
        self.assertEqual(supplier2['upc'], '1122')
        self.assertEqual(supplier2['reference'], 'AHH')
        self.assertEqual(supplier2['purchasing_units'], 'mm')
        
        #Tests the resource in the database
        supply = Supply.objects.get(pk=1)
        self.assertEqual(supply.type, 'Glue')
        
    def test_add(self):
        """
        Tests adding a quantity
        to the specific url
        """
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('10.8'))
        resp = self.api_client.post('/api/v1/supply/1/add?quantity=5', format='json')
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('15.8'))
        
    def test_subract(self):
        """
        Tests adding a quantity
        to the specific url
        """
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('10.8'))
        resp = self.api_client.post('/api/v1/supply/1/subtract?quantity=5', format='json')
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('5.8'))
        
    @unittest.skip('No longer using this method to change quantity')
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
        resp = self.api_client.put('/api/v1/supply/1', format='json',
                                   data=modified_data)
        
        self.assertHttpOK(resp)
        self.assertEqual(Supply.objects.count(), 2)
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('14'))
        self.assertEqual(Supply.objects.get(pk=1).description, 'new')

        #Tests the returned data
        obj = self.deserialize(resp)
        self.assertEqual(float(obj['quantity']), float('14'))
    
    @unittest.skip("no longer using this method to change quantity")
    def test_put_subtract_quantity(self):
        """
        Tests adding quantity to the item
        """
        modified_data = base_supply.copy()
        modified_data['quantity'] = '8'
        
        #Tests the api and the response
        self.assertEqual(Supply.objects.count(), 2)
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('10.8'))
        resp = self.api_client.put('/api/v1/supply/1', format='json',
                                   data=modified_data)
        
        self.assertHttpOK(resp)
        self.assertEqual(Supply.objects.count(), 2)
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('8'))

        #Tests the returned data
        obj = self.deserialize(resp)
        self.assertEqual(float(obj['quantity']), float('8'))
        
#@unittest.skip("Testing supplies only...")
class FabricResourceTestCase(ResourceTestCase):
    
    def setUp(self):
        """
        Set up the view 
        
        -login the user
        """
        super(FabricResourceTestCase, self).setUp()
        
        self.create_user()
        self.api_client.client.login(username='test', password='test')
        
        self.supplier = Supplier(**base_supplier)
        self.supplier.save()
        self.supply = Fabric.create(**base_fabric)
        self.assertIsNotNone(self.supply.pk)
        self.supply2 = Fabric.create(**base_fabric)
        self.assertIsNotNone(self.supply.pk)
        self.product1 = Product(supply=self.supply, supplier=self.supplier,
                                cost=100, purchasing_units='m')
        self.product1.save()
        self.product2 = Product(supply=self.supply2, supplier=self.supplier,
                                cost=100, purchasing_units='m')
        self.product2.save()
        
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
        resp = self.api_client.get('/api/v1/fabric')
        self.assertHttpOK(resp)
        
        #Tests the returned data
        resp_obj = self.deserialize(resp)
        self.assertIn('objects', resp_obj)
        self.assertEqual(len(resp_obj['objects']), 2)
    
    def test_get(self):
        """
        Tests getting a supply that doesn't have the price 
        where the user is not authorized to view the price
        """
        resp = self.api_client.get('/api/v1/fabric/1')
        self.assertHttpOK(resp)
        
        obj = self.deserialize(resp)
        self.assertEqual(float(obj['cost']), float('100'))
        
    def test_get_without_price(self):
        """
        Tests getting a supply that doesn't have the price 
        where the user is not authorized to view the price
        """
        #Delete the view cost permission from the user
        self.user.user_permissions.remove(Permission.objects.get(codename='view_cost', content_type=self.ct))
        
        #tests the response
        resp = self.api_client.get('/api/v1/fabric/1')
        self.assertHttpOK(resp)
        
        #Tests the data returned
        obj = self.deserialize(resp)
        self.assertNotIn("cost", obj)
        
    def test_post(self):
        """
        Tests posting to the server
        """
        #Test creating an objects. 
        self.assertEqual(Supply.objects.count(), 2)
        resp = self.api_client.post('/api/v1/fabric', format='json',
                                    data=base_fabric)
        self.assertHttpCreated(resp)
       
        #Tests the dat aturned
        obj = self.deserialize(resp)
        self.assertEqual(obj['id'], 3)
        self.assertEqual(int(obj['width']), 100)
        self.assertEqual(int(obj['depth']), 0   )
        self.assertEqual(int(obj['height']), 300)
        #self.assertEqual(obj['reference'], 'A2234')
        self.assertEqual(obj['description'], 'test')
        self.assertEqual(int(obj['cost']), 100)
        
    def test_put(self):
        """
        Tests adding quantity to the item
        """
        modified_data = base_supply.copy()
        modified_data['cost'] = '111'
        #Tests the api and the response
        self.assertEqual(Supply.objects.count(), 2)
        resp = self.api_client.put('/api/v1/fabric/1', format='json',
                                   data=modified_data)
        
        self.assertHttpOK(resp)
        self.assertEqual(Supply.objects.count(), 2)

        #Tests the returned data
        obj = self.deserialize(resp)
        self.assertEqual(float(obj['cost']), float('100'))
        
    @unittest.skip("no longer using this method to change quantity")
    def test_put_add_quantity(self):
        """
        Tests adding quantity to the item
        """
        modified_data = base_supply.copy()
        modified_data['quantity'] = '14'
        
        #Tests the api and the response
        self.assertEqual(Supply.objects.count(), 2)
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('10.8'))
        resp = self.api_client.put('/api/v1/fabric/1', format='json',
                                   data=modified_data)
        self.assertHttpOK(resp)
        self.assertEqual(Supply.objects.count(), 2)
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('14'))

        #Tests the returned data
        obj = self.deserialize(resp)
        self.assertEqual(float(obj['quantity']), float('14'))
        
    @unittest.skip("no longer using this method to change quantity")
    def test_put_subtract_quantity(self):
        """
        Tests adding quantity to the item
        """
        modified_data = base_supply.copy()
        modified_data['quantity'] = '8'
        
        #Tests the api and the response
        self.assertEqual(Supply.objects.count(), 2)
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('10.8'))
        resp = self.api_client.put('/api/v1/fabric/1', format='json',
                                   data=modified_data)
        
        self.assertHttpOK(resp)
        self.assertEqual(Supply.objects.count(), 2)
        self.assertEqual(Supply.objects.get(pk=1).quantity, float('8'))

        #Tests the returned data
        obj = self.deserialize(resp)
        self.assertEqual(float(obj['quantity']), float('8'))
        
    @unittest.skip("no longer using this method to change quantity")
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
        resp = self.api_client.put('/api/v1/fabric/1', format='json',
                                   data=modified_data)
        self.assertEqual(Fabric.objects.get(pk=1).quantity, float('10.8'))
        #Tests the data retured
        obj = self.deserialize(resp)
        self.assertEqual(float(obj['quantity']), float('10.8'))
        
    @unittest.skip("no longer using this method to change quantity")
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
        resp = self.api_client.put('/api/v1/fabric/1', format='json',
                                   data=modified_data)
        self.assertEqual(Fabric.objects.get(pk=1).quantity, float('10.8'))
        #Tests the data retured
        obj = self.deserialize(resp)
        self.assertEqual(float(obj['quantity']), float('10.8'))
        