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
from supplies.models import Supply, Fabric, Foam, Log
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
        self.supply = Supply.create(**base_supply)
        self.assertIsNotNone(self.supply.pk)
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
    
    def test_get(self):
        """
        Tests getting a supply that doesn't have the price 
        where the user is not authorized to view the price
        """
        resp = self.api_client.get('/api/v1/supply/1')
        self.assertHttpOK(resp)
        
        obj = self.deserialize(resp)
        #self.assertEqual(Decimal(obj['cost']), Decimal('100'))
        self.assertIn('description', obj)
        self.assertEqual(obj['description'], 'test')
        self.assertIn('type', obj)
        self.assertEqual(obj['type'], 'wood')
        

        resp = self.api_client.get('/api/v1/supply/1?country=TH')
        self.assertHttpOK(resp)
        obj = self.deserialize(resp)
        self.assertEqual(obj['quantity'], 10.8)
        
    def test_get_log(self):
        """
        Tests gettings the log for all the supplies
        """
        
        resp = self.api_client.get('/api/v1/supply/log')
        self.assertHttpOK(resp)
        obj = self.deserialize(resp)
        self.assertIsInstance(obj, list)
    
    @unittest.skip('No longer using this method to change quantity')    
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
        self.assertNotIn("cost", obj)
    
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
        self.assertEqual(obj['reference'], 'A2234')
        self.assertEqual(obj['description'], 'test')
        self.assertEqual(int(obj['cost']), 100)
        self.assertEqual(obj['height_units'], 'yd')
        self.assertEqual(obj['width_units'], 'm')
        self.assertEqual(obj['notes'], 'This is awesome')
        self.assertIn('type', obj)
        self.assertEqual(obj['type'], 'wood')
        
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
        
        #Validate original data
        supply = Supply.objects.get(pk=1)
        supply.country = 'TH'
        self.assertEqual(supply.quantity, 10.8)
        self.assertEqual(Log.objects.all().count(), 0)
        
        #Prepare modified data for PUT
        modified_data = base_supply.copy()
        modified_data['description'] = 'new'
        modified_data['type'] = 'Glue'
        modified_data['quantity'] = 11
        
        #Tests the api and the response
        self.assertEqual(Supply.objects.count(), 2)
        resp = self.api_client.put('/api/v1/supply/1?country=TH', format='json',
                                   data=modified_data)
        
        self.assertHttpOK(resp)
        self.assertEqual(Supply.objects.count(), 2)

        #Tests the returned data
        obj = self.deserialize(resp)
        self.assertEqual(obj['type'], 'Glue')
        self.assertEqual(obj['quantity'], 11)
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
        self.assertEqual(log.message, "Added 0.2ml to test")
        
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
        
@unittest.skip("Testing supplies only...")
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
        self.assertEqual(obj['reference'], 'A2234')
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
        self.assertEqual(float(obj['cost']), float('111'))
        
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
        