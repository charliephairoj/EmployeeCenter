"""
Purchase Order tests
"""
import copy
import random
import logging
import dateutil.parser
import datetime
import subprocess
from decimal import Decimal
import webbrowser
import unittest
from pytz import timezone

from django.test import TestCase
from django.contrib.auth.models import User, Permission, ContentType
from rest_framework.test import APITestCase

from contacts.models import Supplier, Address, SupplierContact
from po.models import PurchaseOrder, Item
from supplies.models import Supply, Fabric, Product, Log
from projects.models import Project
from po.serializers import ItemSerializer


logger = logging.getLogger(__name__)


base_address = {'address1': '22471 Sunbrook',
                'city': 'Mission Viejo',
                'territory': 'CA',
                'zipcode': '92692',
                'country': 'USA'}

base_supplier = {'name': 'Zipper World',
                 'id': 1,
                 'currency': 'USD',
                 #'address': base_address,
                 'terms': 30}

base_fabric = {'pattern': 'Maxx',
               'color': 'Blue',
               'quantity': 10,
               'reference': 'A1',
               'supplier': {'id': 1},
               'unit_cost': 12.11}

base_fabric2 = base_fabric.copy()
base_fabric2['pattern'] = "Cobalt"
base_fabric2['color'] = 'Charcoal'

base_purchase_order = {'supplier': {'id':1},
                       'project': {'id': 1,
                                   'codename': 'MC House'},
                       'deposit': '50',
                       'items': [{'supply':{'id': 1}, 'quantity':10},
                                 {'supply':{'id': 2}, 'quantity': 3}],
                       'vat': '7'}

date = datetime.datetime.now()

def create_user(block_permissions=[]):
    """
    Creates a user
    """
    user = User.objects.create_user('test{0}'.format(random.randint(1, 99999)),
                                    'test',
                                    'test')
    user.name = 'Charlie P'
    user.first_name = 'Charlie'
    user.last_name = 'P'
    user.is_staff = True
    user.save()

    #Add permissions
    for p in Permission.objects.all():
        if p.codename not in block_permissions:
            user.user_permissions.add(p)
    return user


class PurchaseOrderTest(APITestCase):
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
        self.p2 = Permission(codename="change_purchaseorder", content_type=self.ct)
        self.p2.save()
        #Create the user
        self.username = 'tester'
        self.password = 'pass'
        self.user = User.objects.create_user(self.username, 'charliep@dellarobbiathailand.com', self.password)
        self.user.save()
        self.user.user_permissions.add(self.p)
        self.user.user_permissions.add(self.p2)
        self.client.login(username=self.username, password=self.password)
        
        
        self.supplier = Supplier(**base_supplier)
        self.supplier.save()
        self.address = Address(**base_address)
        self.address.contact = self.supplier
        self.address.save()
        self.contact = SupplierContact(name='test', email='test@yahoo.com', telephone=1234, primary=True)
        self.contact.supplier = self.supplier
        self.contact.save()
        self.supply = Fabric.create(**base_fabric)
       
        #self.supply.units = "m^2"
        self.supply.save()
        self.supply1 = self.supply
        
        self.product = Product(supply=self.supply, supplier=self.supplier, cost=base_fabric['unit_cost'],
                               purchasing_units='m')
        self.product.save()
        self.supply2 = Fabric.create(**base_fabric2)
        self.supply2.discount = 5
        self.supply2.save()
        self.product2 = Product(supply=self.supply2, supplier=self.supplier, cost=base_fabric['unit_cost'])
        self.product2.save()
        self.supply.supplier = self.supplier
        self.supply2.supplier = self.supplier
        
        #Create a project
        self.project = Project()
        self.project.codename = 'MC House'
        self.project.save()
        
        self.po = PurchaseOrder()
        self.po.employee = self.user
        self.po.supplier = self.supplier
        self.po.terms = self.supplier.terms
        self.po.vat = 7
        self.po.order_date = datetime.datetime(2014, 3, 2)
        self.po.save()
        #self.po.create_and_upload_pdf()
        
        self.item = Item.create(supplier=self.supplier, id=1, **base_purchase_order['items'][0])
        self.item.purchase_order = self.po
        self.item.save()
        
        self.po.calculate_total()
        self.po.save()
    
    def test_get_list(self):
        """
        Tests getting a list of po's via GET
        """
        #Validate the response
        resp = self.client.get('/api/v1/purchase-order/', format='json')
        self.assertEqual(resp.status_code, 200)
        
        #Validate the returned data
        resp = resp.data
        self.assertIsInstance(resp, dict)
        self.assertIsInstance(resp['results'], list)
        self.assertEqual(len(resp['results']), 1)
    
    def test_get(self):
        """
        Tests getting a single resource via GET
        """
        #Validate the response
        resp = self.client.get('/api/v1/purchase-order/1/')
        self.assertEqual(resp.status_code, 200)
        
        #Validate the returned data
        obj = resp.data
        self.assertEqual(obj['id'], 1)
        self.assertEqual(obj['terms'], 30)
        self.assertEqual(obj['revision'], 0)
        
        #Test items
        self.assertIn('items', obj)
        self.assertEqual(len(obj['items']), 1)
        item1 = obj['items'][0]
        #self.assertIn('purchasing_units', item1)
        #self.assertEqual(item1['purchasing_units'], 'm')
    
    def test_get_with_pdf(self):
        """
        Tests getting a resource with the pdf
        """
        self.skipTest("")
        self.po.create_and_upload_pdf()
        
        resp = self.client.get('/api/v1/purchase-order/1/')
        self.assertEqual(resp.status_code, 200)
        
        obj = resp.data
        self.assertIn('pdf', obj)
        self.assertIn('url', obj['pdf'])
        self.assertIsNotNone(obj['pdf']['url'])

    def test_post(self):
        """
        Tests creating a new resource via POST
        """

        print '\n'
        logger.debug("Creating new po")
        print '\n'
        
        #validate the response
        resp = self.client.post('/api/v1/purchase-order/',
                                data=base_purchase_order, 
                                format='json')
        self.assertEqual(resp.status_code, 201, msg=resp)
        
        #Validate the data returned
        obj = resp.data
        self.assertEqual(obj['id'], 2)
        self.assertIsNotNone(obj['items'])
        self.assertIsInstance(obj['items'], list)
        self.assertEqual(len(obj['items']), 2)
        self.assertEqual(obj['currency'], 'USD')
        self.assertIn('project', obj)
        self.assertIsInstance(obj['project'], dict)
        self.assertEqual(obj['project']['id'], 1)
        self.assertEqual(obj['project']['codename'], 'MC House')

        #validate the resource in the database
        po = PurchaseOrder.objects.get(pk=2)
        self.assertIsInstance(po.project, Project)
        #self.assertIsNotNone(obj['pdf'])
        #self.assertIsNotNone(obj['pdf']['url'])
        self.items = po.items.all().order_by('id')
        self.item1 = self.items[0]
        self.item2 = self.items[1]
        self.assertIsInstance(self.item1, Item)
        self.assertIsInstance(self.item1.supply, Supply)
        self.assertEqual(self.item1.supply.id, 1)
        self.assertEqual(self.item1.unit_cost, Decimal('12.11'))
        self.assertEqual(self.item1.quantity, 10)
        self.assertEqual(self.item1.total, Decimal('121.1'))
        self.assertIsInstance(self.item2, Item)
        self.assertIsInstance(self.item2.supply, Supply)
        self.assertEqual(self.item2.supply.id, 2)
        self.assertEqual(self.item2.unit_cost, Decimal('12.11'))
        self.assertEqual(self.item2.quantity, 3)
        self.assertEqual(self.item2.total, Decimal('34.51'))
        
        self.assertEqual(Project.objects.count(), 1)
        project = Project.objects.all()[0]
        self.assertIsInstance(project, Project)
        self.assertEqual(project.id, 1)
        self.assertEqual(project.codename, 'MC House')
    
    def test_post_with_new_project(self):
        """
        Tests creating a new resource via POST
        """
        print '\n'
        logger.debug("Creating new po with a project")
        print '\n'
        
        #validate the response
        po = base_purchase_order.copy()
        po['project'] = {'codename': 'Ladawan'}
        po['currency'] = 'RMB'
        resp = self.client.post('/api/v1/purchase-order/',
                                data=po,
                                format='json')
        self.assertEqual(resp.status_code, 201, msg=resp)
        
        #Validate the data returned
        obj = resp.data
        self.assertEqual(obj['id'], 2)
        self.assertIsNotNone(obj['items'])
        self.assertIsInstance(obj['items'], list)
        self.assertEqual(len(obj['items']), 2)
        self.assertIn('project', obj)
        self.assertIsInstance(obj['project'], dict)
        self.assertEqual(obj['project']['id'], 2)
        self.assertEqual(obj['project']['codename'], 'Ladawan')
        self.assertEqual(obj['currency'], 'RMB')
        
        #validate the resource in the database
        po = PurchaseOrder.objects.get(pk=2)
        self.assertIsInstance(po.project, Project)
        #self.assertIsNotNone(obj['pdf'])
        #self.assertIsNotNone(obj['pdf']['url'])
        self.items = po.items.all().order_by('id')
        self.item1 = self.items[0]
        self.item2 = self.items[1]
        self.assertIsInstance(self.item1, Item)
        self.assertIsInstance(self.item1.supply, Supply)
        self.assertEqual(self.item1.supply.id, 1)
        self.assertEqual(self.item1.unit_cost, Decimal('12.11'))
        self.assertEqual(self.item1.quantity, 10)
        self.assertEqual(self.item1.total, Decimal('121.1'))
        self.assertIsInstance(self.item2, Item)
        self.assertIsInstance(self.item2.supply, Supply)
        self.assertEqual(self.item2.supply.id, 2)
        #self.assertEqual(self.item2.unit_cost, Decimal('11.50'))
        self.assertEqual(self.item2.quantity, 3)
        self.assertEqual(self.item2.total, Decimal('34.51'))
        
        project = po.project
        self.assertEqual(Project.objects.all().count(), 2)
        self.assertIsInstance(project, Project)
        self.assertEqual(project.id, 2)
        self.assertEqual(project.codename, 'Ladawan')
    
    def test_creating_new_po_with_price_change(self):
        """
        Tests creating a new po via post while also changing the price of a supply
        """
        print '\n'
        logger.debug("Creating new po with a price change")
        print '\n'
        #validate the response
        po = copy.deepcopy(base_purchase_order)
        del po['items'][1]
        po['items'][0]['cost'] = '1.99'
        resp = self.client.post('/api/v1/purchase-order/',
                                data=po,
                                format='json')
        self.assertEqual(resp.status_code, 201, msg=resp)
        resp_obj = resp.data
        #webbrowser.get("open -a /Applications/Google\ Chrome.app %s").open(resp_obj['pdf']['url'])
        
        #Verify the returned data
        self.assertEqual(resp_obj['id'], 2)
        self.assertEqual(resp_obj['vat'], 7)
        self.assertEqual(Decimal(resp_obj['grand_total']), Decimal('21.30'))
        item = resp_obj['items'][0]
        self.assertEqual(Decimal(item['unit_cost']), Decimal('1.99'))
        self.assertEqual(Decimal(item['total']), Decimal('19.90'))
        
        #Verify data in the database
        supply = Supply.objects.get(pk=1)
        supply.supplier = self.supplier
        self.assertEqual(supply.cost, Decimal('1.99'))
        self.assertEqual(Log.objects.all().count(), 1)
        log = Log.objects.all()[0]
        self.assertEqual(log.message, "Price change from 12.11USD to 1.99USD for Pattern: Maxx, Col: Blue [Supplier: Zipper World]")
        
    def test_creating_new_po_with_different_currency(self):
        """
        Tests creating a new po via post while also changing the price of a supply
        """
        print '\n'
        logger.debug("Creating new po with a price change")
        print '\n'
        #validate the response
        po = copy.deepcopy(base_purchase_order)
        del po['items'][1]
        po['items'][0]['cost'] = '1.99'
        po['currency'] = 'RMB'
        resp = self.client.post('/api/v1/purchase-order/',
                                data=po,
                                format='json')
        self.assertEqual(resp.status_code, 201, msg=resp)
        resp_obj = resp.data
        #webbrowser.get("open -a /Applications/Google\ Chrome.app %s").open(resp_obj['pdf']['url'])
        
        #Verify the returned data
        self.assertEqual(resp_obj['id'], 2)
        self.assertEqual(resp_obj['vat'], 7)
        self.assertEqual(resp_obj['currency'], 'RMB')
        self.assertEqual(Decimal(resp_obj['grand_total']), Decimal('21.30'))
        item = resp_obj['items'][0]
        self.assertEqual(Decimal(item['unit_cost']), Decimal('1.99'))
        self.assertEqual(Decimal(item['total']), Decimal('19.90'))
        
        po = PurchaseOrder.objects.get(pk=2)
        self.assertEqual(po.currency, 'RMB')
        
    def test_updating_the_po(self):
        """
        Tests updating the purchase order
        via a PUT request
        """
        print '\n'
        logger.debug('Updating PO')
        print '\n'
        
        #Verifying po in database
        self.assertEqual(self.po.id, 1)
        self.assertEqual(self.po.items.count(), 1)
        self.assertEqual(self.po.grand_total, Decimal('129.58'))
        self.assertEqual(self.po.order_date.date(), datetime.now().date())
        item = self.po.items.all()[0]
        self.assertEqual(item.id, 1)
        self.assertEqual(item.quantity, 10)
        self.assertEqual(item.total, Decimal('121.1'))
        
        modified_po_data = copy.deepcopy(base_purchase_order)
        del modified_po_data['items'][0]
        modified_po_data['items'][0]['id'] = 1
        modified_po_data['items'][0]['comments'] = 'test change'
        modified_po_data['items'][0]['description'] = "test description change"
        modified_po_data['status'] = 'PROCESSED'
        
        resp = self.client.put('/api/v1/purchase-order/1/',
                                   format='json',
                                   data=modified_po_data)
        
        #Verify the response
        self.assertEqual(resp.status_code, 200, msg=resp)
        po = resp.data
        self.assertEqual(po['id'], 1)
        self.assertEqual(po['supplier']['id'], 1)
        self.assertEqual(po['vat'], 7)
        self.assertEqual(Decimal(po['grand_total']), Decimal('38.88'))
        self.assertEqual(po['discount'], 0)
        self.assertEqual(po['revision'], 1)
        self.assertEqual(len(po['items']), 1)
        #self.assertEqual(po['status'], 'PAID')
        #Check the new pdf
        #webbrowser.get("open -a /Applications/Google\ Chrome.app %s").open(po['pdf']['url'])
        
        item2 = po['items'][0]
       
        self.assertEqual(item2['id'], 1)
        self.assertEqual(item2['quantity'], '3.0000000000')
        self.assertEqual(item2['comments'], 'test change')
        self.assertEqual(item2['description'], 'test description change')
        self.assertEqual(Decimal(item2['unit_cost']), Decimal('12.11'))
        self.assertEqual(Decimal(item2['total']), Decimal('36.33'))
        
        #Verify database record
        po = PurchaseOrder.objects.get(pk=1)
        
        self.assertEqual(po.supplier.id, 1)
        self.assertEqual(po.status, 'PROCESSED')
        self.assertEqual(po.order_date.date(), datetime.datetime.now(timezone('Asia/Bangkok')).date())
        self.assertEqual(po.vat, 7)
        self.assertEqual(po.grand_total, Decimal('38.88'))
        self.assertEqual(po.items.count(), 1)
        
        item2 = po.items.all().order_by('id')[0]
        self.assertEqual(item2.id, 1)
        self.assertEqual(item2.description, 'test description change')
        self.assertEqual(item2.comments, 'test change')
        self.assertEqual(item2.quantity, 3)
        self.assertEqual(item2.unit_cost, Decimal('12.11'))
        self.assertEqual(item2.total, Decimal('36.33'))
    
    def test_updating_po_items(self):
        """
        Test updating properties of items in the purchase order
        
        """
        print '\n'
        logger.debug('Updating items')
        print '\n'
        
        modified_po_data = copy.deepcopy(base_purchase_order)
        modified_po_data['status'] = 'PROCESSED'
        modified_po_data['items'][0]['purchasing_units'] = 'set'

        resp = self.client.put('/api/v1/purchase-order/1/', format='json', data=modified_po_data)
        
        po = resp.data
        item1 = po['items'][0]
        #self.assertIn('purchasing_units', item1)
        #self.assertEqual(item1['purchasing_units'], 'set')
        
    def test_updating_po_with_discount(self):
        """
        """
        print '\n'
        logger.debug("Update purchase order with a discount for individual supply")
        print '\n'
        
        #Verify the original po
        self.assertEqual(self.po.id, 1)
        self.assertEqual(self.po.items.count(), 1)
        self.assertEqual(self.po.grand_total, Decimal('129.58'))
        item = self.po.items.all()[0]
        self.assertEqual(item.id, 1)
        self.assertEqual(item.quantity, 10)
        self.assertEqual(item.total, Decimal('121.1'))
        
        modified_po = copy.deepcopy(base_purchase_order)
        modified_po['items'][0]['discount'] = 50
        modified_po['items'][0]['id'] = 1
        modified_po['status'] = 'PROCESSED'
        self.assertEqual(len(modified_po['items']), 2)
        
        resp = self.client.put('/api/v1/purchase-order/1/',
                                format='json',
                                data=modified_po)
        self.assertEqual(resp.status_code, 200, msg=resp)
        resp_obj = resp.data
        self.assertEqual(resp_obj['revision'], 1)
        #Check the new pdf
        #webbrowser.get("open -a /Applications/Google\ Chrome.app %s").open(resp_obj['pdf']['url'])
        
        item1 = resp_obj['items'][0]
        item2 = resp_obj['items'][1]
        self.assertEqual(item1['id'], 1)
        self.assertEqual(item1['quantity'], '10.0000000000')
        self.assertEqual(Decimal(item1['unit_cost']), Decimal('12.11'))
        self.assertEqual(Decimal(item1['total']), Decimal('60.55'))
        self.assertEqual(item2['id'], 2)
        self.assertEqual(item2['quantity'], '3.0000000000')
        self.assertEqual(item2['discount'], 5)
        self.assertEqual(Decimal(item2['unit_cost']), Decimal('12.11'))
        self.assertEqual(Decimal(item2['total']), Decimal('34.51'))
        self.assertEqual(Decimal(resp_obj['grand_total']), Decimal('101.72'))
        
        po = PurchaseOrder.objects.get(pk=1)
        item1 = po.items.order_by('id').all()[0]
        self.assertEqual(item1.id, 1)
        self.assertEqual(item1.quantity, Decimal('10.00'))
        self.assertEqual(item1.discount, 50)
        self.assertEqual(item1.unit_cost, Decimal('12.11'))
        self.assertEqual(item1.total, Decimal('60.55'))
        item2 = po.items.order_by('id').all()[1]
        self.assertEqual(item2.id, 2)
        self.assertEqual(item2.quantity, Decimal('3.00'))
        self.assertEqual(item2.unit_cost, Decimal('12.11'))
        self.assertEqual(item2.discount, 5)
        self.assertEqual(item2.total, Decimal('34.51'))
        
    def test_updating_po_with_new_currency(self):
        """
        Test updating the status of supplies and automatically checking in supplies 
        """
        #test original quantity
        
        modified_po = copy.deepcopy(base_purchase_order)
        modified_po['currency'] = 'RMB'
        
        resp = self.client.put('/api/v1/purchase-order/1/',
                               format='json',
                               data=modified_po)
                               
        self.assertEqual(resp.status_code, 200, msg=resp)
        
        po = resp.data
        
        self.assertEqual(po['currency'], 'RMB')
        
    def test_updating_the_supply_price(self):
        """
        Test updating a po with a new cost for an item
        """
        self.assertEqual(self.po.id, 1)
        self.assertEqual(self.po.items.count(), 1)
        item = self.po.items.all()[0]
        self.assertEqual(item.id, 1)
        self.assertEqual(item.unit_cost, Decimal('12.11'))
        self.assertEqual(Log.objects.all().count(), 0)
        
        modified_po = copy.deepcopy(base_purchase_order)
        modified_po['items'][0]['unit_cost'] = Decimal('10.05')
        modified_po['items'][0]['id'] = 1
        modified_po['status'] = 'PROCESSED'
        del modified_po['items'][1]
        resp = self.client.put('/api/v1/purchase-order/1/',
                                format='json',
                                data=modified_po)
        self.assertEqual(resp.status_code, 200, msg=resp)
        resp_obj = resp.data
        self.assertEqual(resp_obj['revision'], 1)
        #Check the new pdf
        #webbrowser.get("open -a /Applications/Google\ Chrome.app %s").open(resp_obj['pdf']['url'])
        
        self.assertEqual(resp_obj['id'], 1)
        self.assertEqual(resp_obj['supplier']['id'], 1)
        self.assertEqual(resp_obj['vat'], 7)
        self.assertEqual(resp_obj['discount'], 0)
        self.assertEqual(resp_obj['revision'], 1)
        self.assertEqual(Decimal(resp_obj['grand_total']), Decimal('107.54'))
        item1 = resp_obj['items'][0]
        self.assertEqual(item1['id'], 2)
        self.assertEqual(item1['quantity'], '10.0000000000')
        self.assertEqual(Decimal(item1['unit_cost']), Decimal('10.05'))
        self.assertEqual(Decimal(item1['total']), Decimal('100.50'))
       
        #Confirm cost change for item and supply in the database
        po = PurchaseOrder.objects.get(pk=1)
        self.assertEqual(po.grand_total, Decimal('107.54'))
        item1 = po.items.order_by('id').all()[0]
        self.assertEqual(item1.id, 1)
        self.assertEqual(item1.quantity, 10)
        self.assertEqual(item1.unit_cost, Decimal('10.05'))
        supply = item1.supply
        supply.supplier = po.supplier
        self.assertEqual(supply.cost, Decimal('10.05'))
        
        self.assertEqual(Log.objects.all().count(), 1)
        log = Log.objects.all()[0]
        self.assertEqual(log.cost, Decimal('10.05'))
        self.assertEqual(log.supply, supply)
        self.assertEqual(log.supplier, po.supplier)
        self.assertEqual(log.message, "Price change from 12.11USD to 10.05USD for Pattern: Maxx, Col: Blue [Supplier: Zipper World]")
       
    def test_updating_item_status(self):
        """
        Test updating the status of supplies and automatically checking in supplies 
        """
        #test original quantity
        self.assertEqual(self.supply1.quantity, 10)
        self.assertEqual(self.supply2.quantity, 10)
        
        modified_po = copy.deepcopy(base_purchase_order)
        modified_po['status'] = 'Received'
        modified_po['items'][0]['id'] = 1
        #modified_po['items'][0]['status'] = 'Receieved'
            
        resp = self.client.put('/api/v1/purchase-order/1/',
                               format='json',
                               data=modified_po)
                               
        self.assertEqual(resp.status_code, 200, msg=resp)
        
        po = resp.data
        
        self.assertEqual(Supply.objects.get(pk=1).quantity, 20)
        
    def test_updating_the_project(self):
        """
        Tests updating the project, phase, and room of a purchase order
        """
        modified_po = copy.deepcopy(base_purchase_order)
        
        
    def test_updating_to_receive_items(self):
        """
        Test updating the status of the po in order to to receive it
        
        When a purchase order is received, the items received should automatically be added to the 
        supply inventory quantity
        """
        modified_po = copy.deepcopy(base_purchase_order)
        modified_po['items'][0]['id'] = 1
        modified_po['items'][0]['status'] = 'RECEIVED'
        modified_po['status'] = 'RECEIVED'
        self.assertEqual(Supply.objects.get(pk=1).quantity, 10)
        
        resp = self.client.put('/api/v1/purchase-order/1/', format='json', data=modified_po)
        
        self.assertEqual(resp.status_code, 200, msg=resp)
        
        po_data = resp.data
        self.assertEqual(po_data['id'], 1)
        self.assertEqual(po_data['status'], 'RECEIVED')
        
        item1 = po_data['items'][0]
        self.assertEqual(item1['id'], 1)
        self.assertEqual(item1['status'], 'RECEIVED')
        
        #Test database values
        po = PurchaseOrder.objects.get(pk=1)
        self.assertEqual(po.id, 1)
        self.assertEqual(po.status, 'RECEIVED')
        for item in po.items.all():
            self.assertEqual(item.status, "RECEIVED")
            
        supply = Supply.objects.get(pk=1)
        self.assertEqual(supply.quantity, 20)
        log = Log.objects.all().order_by('-id')[0]
        self.assertEqual(log.action, "ADD")
        self.assertEqual(log.quantity, 10)
        self.assertEqual(log.supplier.id, 1)
        self.assertEqual(log.message, "Received 10m of Pattern: Maxx, Col: Blue from Zipper World")
            
        
class ItemTest(TestCase):
    """
    Tests the PO Item
    """
    def setUp(self):
        """
        Set up dependent objects
        """
        super(ItemTest, self).setUp()
        
        self.ct = ContentType(app_label="po")
        self.ct.save()
        self.p = Permission(codename="add_purchaseorder", content_type=self.ct)
        self.p.save()
        self.p2 = Permission(codename="change_purchaseorder", content_type=self.ct)
        self.p2.save()
        
        #Create the user
        self.username = 'tester'
        self.password = 'pass'
        self.user = User.objects.create_user(self.username, 'charliep@dellarobbiathailand.com', self.password)
        self.user.save()
        self.user.user_permissions.add(self.p)
        self.user.user_permissions.add(self.p2)
        self.client.login(username=self.username, password=self.password)
        
        
        self.supplier = Supplier(**base_supplier)
        self.supplier.save()
        self.address = Address(**base_address)
        self.address.contact = self.supplier
        self.address.save()
        self.contact = SupplierContact(name='test', email='test@yahoo.com', telephone=1234, primary=True)
        self.contact.supplier = self.supplier
        self.contact.save()
        
        
        self.supply = Fabric.create(**base_fabric)
       
        #self.supply.units = "m^2"
        self.supply.save()
        
        self.po = PurchaseOrder()
        self.po.employee = self.user
        self.po.supplier = self.supplier
        self.po.terms = self.supplier.terms
        self.po.vat = 7
        self.po.order_date = datetime.datetime(2014, 3, 2)
        self.po.save()
        
        self.item = Item(unit_cost=Decimal('13.55'), quantity=Decimal('10'), supply=self.supply)
        self.item.description = self.supply.description
        self.item.purchase_order = self.po
        self.item.save()

    def test_creating_item_with_no_product_with_unit_cost(self):
        """Test creating a item via the serializer where there is no product
        """
        context = {'po': self.po,
                   'supplier': self.supplier}
        data = {'supply': self.supply.id,
                'unit_cost': 10,
                'quantity': 5,
                'units': 'yd'}
                
        item_serializer = ItemSerializer(context=context, data=data)
        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()
            
        # Verify product is created
        self.assertEqual(Product.objects.filter(supply=self.supply, supplier=self.supplier).count(), 1)
        
        # Verify item
        resp_data = item_serializer.data
        
        self.assertEqual(resp_data['description'], 'Pattern: Maxx, Col: Blue')
        self.assertEqual(resp_data['units'], 'yd')
        self.assertEqual(Decimal(resp_data['quantity']), Decimal('5'))
        self.assertEqual(Decimal(resp_data['total']), Decimal('50'))
        
    def test_creating_item_with_product_with_no_unit_cost(self):
        """Test creating a item via the serializer where there is no product
        """
        Product.objects.create(supply=self.supply, supplier=self.supplier, cost=Decimal('12.11'), 
                               purchasing_units="yd")
        
        context = {'po': self.po,
                   'supplier': self.supplier}
        data = {'supply': self.supply.id,
                'quantity': 5,
                'units': 'yd'}
                
        item_serializer = ItemSerializer(context=context, data=data)
        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()
            
        # Verify product is created
        self.assertEqual(Product.objects.filter(supply=self.supply, supplier=self.supplier).count(), 1)
        
        # Verify item
        resp_data = item_serializer.data
        
        self.assertEqual(resp_data['description'], 'Pattern: Maxx, Col: Blue')
        self.assertEqual(resp_data['units'], 'yd')
        self.assertEqual(Decimal(resp_data['quantity']), Decimal('5'))
        self.assertEqual(Decimal(resp_data['total']), Decimal('60.55'))
        
    def test_updating_item_without_product(self):
        
        context = {'po': self.po,
                   'supplier': self.supplier}
        data = {'supply': self.supply.id,
                'unit_cost': Decimal('11.22'),
                'quantity': 4,
                'units': 'yd'}
        
        # Verify there is no product
        self.assertEqual(Product.objects.filter(supply=self.supply, supplier=self.supplier).count(), 0)
        
        # Update item
        item_serializer = ItemSerializer(self.item, context=context, data=data)
        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()
            
        # Verify product is created
        self.assertEqual(Product.objects.filter(supply=self.supply, supplier=self.supplier).count(), 1)
        
        # Verify item
        resp_data = item_serializer.data
        
        self.assertEqual(resp_data['description'], 'Pattern: Maxx, Col: Blue')
        self.assertEqual(resp_data['units'], 'yd')
        self.assertEqual(Decimal(resp_data['quantity']), Decimal('4'))
        self.assertEqual(Decimal(resp_data['total']), Decimal('44.88'))
        
    def test_updating_item_with_product(self):
        Product.objects.create(supply=self.supply, supplier=self.supplier, cost=Decimal('12.11'), 
                               purchasing_units="yd")
                               
        context = {'po': self.po,
                   'supplier': self.supplier}
        data = {'supply': self.supply.id,
                'unit_cost': Decimal('11.22'),
                'quantity': 4,
                'units': 'm'}
        
        # Verify there is a product
        products = Product.objects.filter(supply=self.supply, supplier=self.supplier)
        self.assertEqual(products.count(), 1)
        self.assertEqual(products[0].cost, Decimal('12.11'))
        self.assertEqual(products[0].purchasing_units, 'yd')
        
        # Update item
        item_serializer = ItemSerializer(self.item, context=context, data=data)
        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()
            
        # Verify product is created
        products2 = Product.objects.filter(supply=self.supply, supplier=self.supplier)
        self.assertEqual(products2.count(), 1)
        self.assertEqual(products2[0].cost, Decimal('11.22'))
        self.assertEqual(products2[0].purchasing_units, 'm')

        # Verify item
        resp_data = item_serializer.data
        
        self.assertEqual(resp_data['description'], 'Pattern: Maxx, Col: Blue')
        self.assertEqual(resp_data['units'], 'm')
        self.assertEqual(Decimal(resp_data['quantity']), Decimal('4'))
        self.assertEqual(Decimal(resp_data['total']), Decimal('44.88'))
    

   
    
   
