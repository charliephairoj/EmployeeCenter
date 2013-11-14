"""
Purchase Order tests
"""
import random
import dateutil.parser
import datetime
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User, Permission, ContentType
from tastypie.test import ResourceTestCase

from contacts.models import Supplier, Address
from po.models import PurchaseOrder, Item
from supplies.models import Supply, Fabric

base_address = {'address1': '22471 Sunbrook',
                'city': 'Mission Viejo',
                'territory': 'CA',
                'zipcode': '92692',
                'country': 'USA'}

base_supplier = {'name': 'Zipper World',
                 'id': 1,
                 'currency': 'THB',
                 #'address': base_address,
                 'terms': 30}

base_fabric = {'pattern': 'Maxx',
               'color': 'Blue',
               'quantity': 10,
               'reference': 'A1',
               'supplier': {'id': 1},
               'unit_cost': 12.11}

base_purchase_order = {'supplier': {'id':1},
                       'items': [{'id': 1, 'quantity':10}],
                       'vat': '7'}

date = datetime.datetime.now()

def create_user(block_permissions=[]):
    """
    Creates a user
    """
    user = User.objects.create_user('test{0}'.format(random.randint(1, 99999)),
                                    'test',
                                    'test')
    user.is_staff = True
    user.save()

    #Add permissions
    for p in Permission.objects.all():
        if p.codename not in block_permissions:
            user.user_permissions.add(p)
    return user


class PurchaseOrderTest(ResourceTestCase):
    """
    Tests the Purchase Order
    """
    def setUp(self):
        """
        Set up dependent objects
        """
        super(PurchaseOrderTest, self).setUp()
        
        self.ct = ContentType(app_label="po")
        self.ct.save()
        self.p = Permission(codename="add_purchaseorder", content_type=self.ct)
        self.p.save()
        #Create the user
        self.username = 'tester'
        self.password = 'pass'
        self.user = User.objects.create_user(self.username, 'test@yahoo.com', self.password)
        self.user.save()
        self.user.user_permissions.add(self.p)
        self.api_client.client.login(username=self.username, password=self.password)
        
        
        self.supplier = Supplier(**base_supplier)
        self.supplier.save()
        self.address = Address(**base_address)
        self.address.contact = self.supplier
        self.address.save()
        self.supply = Fabric.create(**base_fabric)
        self.supply.save()
        
        self.po = PurchaseOrder()
        self.po.employee = self.user
        self.po.supplier = self.supplier
        self.po.terms = self.supplier.terms
        self.po.save()
        
        
    def test_get_list(self):
        """
        Tests getting a list of po's via GET
        """
        #Validate the response
        resp = self.api_client.get('/api/v1/purchase-order', format='json')
        self.assertHttpOK(resp)
        self.assertValidJSONResponse(resp)
        
        #Validate the returned data
        resp = self.deserialize(resp)
        self.assertIsInstance(resp, dict)
        self.assertIsInstance(resp['objects'], list)
        self.assertEqual(len(resp['objects']), 1)
        
    def test_get(self):
        """
        Tests getting a single resource via GET
        """
        #Validate the response
        resp = self.api_client.get('/api/v1/purchase-order/1')
        self.assertHttpOK(resp)
        self.assertValidJSONResponse(resp)
        
        #Validate the returned data
        obj = self.deserialize(resp)
        self.assertEqual(obj['id'], 1)
        self.assertEqual(obj['terms'], 30)
        
    def test_post(self):
        """
        Tests creating a new resource via POST
        """
        #validate the response
        resp = self.api_client.post('/api/v1/purchase-order',
                                    data=base_purchase_order)
        self.assertHttpCreated(resp)
        
        #Validate the data returned
        obj = self.deserialize(resp)
        self.assertEqual(obj['id'], 2)
        self.assertIsNotNone(obj['items'])
        self.assertIsInstance(obj['items'], list)
        print obj['pdf']['url']
        
    
    
    

class ItemTest(TestCase):
    """
    Tests the PO Item
    """
    def setUp(self):
        self.supplier = Supplier(**base_supplier)
        self.supply.save()
        self.supply = Fabric.create(**base_fabric)
    
   
