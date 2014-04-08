"""
Purchase Order tests
"""
import random
import logging
import dateutil.parser
import datetime
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User, Permission, ContentType
from tastypie.test import ResourceTestCase

from contacts.models import Supplier, Address, SupplierContact
from po.models import PurchaseOrder, Item
from supplies.models import Supply, Fabric, Product


logger = logging.getLogger(__name__)

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

base_fabric2 = base_fabric.copy()
base_fabric2['pattern'] = "Cobalt"
base_fabric2['color'] = 'Charcoal'

base_purchase_order = {'supplier': {'id':1},
                       'project': 'MC House',
                       'items': [{'id': 1, 'quantity':10},
                                 {'id': 2, 'quantity': 3}],
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
        self.p2 = Permission(codename="change_purchaseorder", content_type=self.ct)
        self.p2.save()
        #Create the user
        self.username = 'tester'
        self.password = 'pass'
        self.user = User.objects.create_user(self.username, 'test@yahoo.com', self.password)
        self.user.save()
        self.user.user_permissions.add(self.p)
        self.user.user_permissions.add(self.p2)
        self.api_client.client.login(username=self.username, password=self.password)
        
        
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
        self.product = Product(supply=self.supply, supplier=self.supplier, cost=base_fabric['unit_cost'])
        self.product.save()
        self.supply2 = Fabric.create(**base_fabric2)
        self.supply2.discount = 5
        self.supply2.save()
        self.product2 = Product(supply=self.supply2, supplier=self.supplier, cost=base_fabric['unit_cost'])
        self.product2.save()
        self.supply.supplier = self.supplier
        self.supply2.supplier = self.supplier
        
        self.po = PurchaseOrder()
        self.po.employee = self.user
        self.po.supplier = self.supplier
        self.po.terms = self.supplier.terms
        self.po.vat = 7
        self.po.save()
        #self.po.create_and_upload_pdf()
        
        self.item = Item.create(supplier=self.supplier, **base_purchase_order['items'][0])
        self.item.purchase_order = self.po
        self.item.save()
        
        self.po.calculate_total()
        self.po.save()
        
    def test_get_list(self):
        """
        Tests getting a list of po's via GET
        """
        self.skipTest('isolate')
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
        self.skipTest('isolate')
        #Validate the response
        resp = self.api_client.get('/api/v1/purchase-order/1')
        self.assertHttpOK(resp)
        self.assertValidJSONResponse(resp)
        
        #Validate the returned data
        obj = self.deserialize(resp)
        self.assertEqual(obj['id'], 1)
        self.assertEqual(obj['terms'], 30)
        self.assertEqual(obj['project'], None)
        self.assertNotIn('pdf', obj)
        
    def test_get_with_pdf(self):
        """
        Tests getting a resource with the pdf
        """
        self.skipTest('isolate')
        self.po.create_and_upload_pdf()
        
        resp = self.api_client.get('/api/v1/purchase-order/1?pdf=true')
        self.assertHttpOK(resp)
        self.assertValidJSONResponse(resp)
        
        obj = self.deserialize(resp)
        self.assertIn('pdf', obj)
        self.assertIn('url', obj['pdf'])
        self.assertIsNotNone(obj['pdf']['url'])

        
    def test_post(self):
        """
        Tests creating a new resource via POST
        """
        self.skipTest('isolate')
        #validate the response
        resp = self.api_client.post('/api/v1/purchase-order',
                                    data=base_purchase_order)
        self.assertHttpCreated(resp)
        
        #Validate the data returned
        obj = self.deserialize(resp)
        self.assertEqual(obj['id'], 2)
        self.assertIsNotNone(obj['items'])
        self.assertIsInstance(obj['items'], list)
        self.assertEqual(len(obj['items']), 2)
        self.assertIn('project', obj)
        self.assertEqual(obj['project'], 'MC House')
        
        #validate the resource in the database
        po = PurchaseOrder.objects.get(pk=2)
        self.assertIsNotNone(po.project)
        self.assertEqual(po.project, 'MC House')
        self.assertIsNotNone(obj['pdf'])
        self.assertIsNotNone(obj['pdf']['url'])
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
        self.assertEqual(self.item2.unit_cost, Decimal('11.50'))
        self.assertEqual(self.item2.quantity, 3)
        logger.debug(self.item1.unit_cost)
        logger.debug(self.item1.total)
        logger.debug(self.item2.unit_cost)
        logger.debug(self.item2.total)
        self.assertEqual(self.item2.total, Decimal('34.5'))
    
    
    def test_updating_the_po(self):
        """
        Tests updating the purchase order
        via a PUT request
        """
        #Verify the original po
        self.assertEqual(self.po.id, 1)
        self.assertEqual(self.po.items.count(), 1)
        self.assertEqual(self.po.grand_total, Decimal('129.58'))
        item = self.po.items.all()[0]
        self.assertEqual(item.id, 1)
        self.assertEqual(item.quantity, 10)
        self.assertEqual(item.total, Decimal('121.1'))
        
        modified_po_data = base_purchase_order.copy()
        modified_po_data['items'][0]['quantity'] = 2
        
        resp = self.api_client.put('/api/v1/purchase-order/1',
                                   format='json',
                                   data=modified_po_data)
        
        #Verify the response
        self.assertHttpOK(resp)
        po = self.deserialize(resp)
        self.assertEqual(po['id'], 1)
        self.assertEqual(po['supplier']['id'], 1)
        self.assertEqual(po['vat'], 7)
        self.assertEqual(po['grand_total'], '62.83')
        self.assertEqual(len(po['items']), 2)
        item1 = po['items'][0]
        item2 = po['items'][1]
        self.assertEqual(item1['id'], 1)
        self.assertEqual(item1['quantity'], 2)
        self.assertEqual(item1['unit_cost'], '12.11')
        self.assertEqual(item1['total'], '24.22')
        self.assertEqual(item2['id'], 2)
        self.assertEqual(item2['quantity'], 3)
        self.assertEqual(item2['unit_cost'], '11.5')
        self.assertEqual(item2['total'], '34.5')
        
        #Verify database record
        po = PurchaseOrder.objects.get(pk=1)
        self.assertEqual(po.supplier.id, 1)
        self.assertEqual(po.vat, 7)
        self.assertEqual(po.grand_total, Decimal('62.83'))
        self.assertEqual(po.items.count(), 2)
        item1 = po.items.all().order_by('id')[0]
        item2 = po.items.all().order_by('id')[1]
        self.assertEqual(item1.id, 1)
        self.assertEqual(item1.quantity, 2)
        self.assertEqual(item1.unit_cost, Decimal('12.11'))
        self.assertEqual(item1.total, Decimal('24.22'))
        self.assertEqual(item2.id, 2)
        self.assertEqual(item2.quantity, 3)
        self.assertEqual(item2.unit_cost, Decimal('11.5'))
        self.assertEqual(item2.total, Decimal('34.5'))
        
        
        
class ItemTest(TestCase):
    """
    Tests the PO Item
    """
    def setUp(self):
        self.supplier = Supplier(**base_supplier)
        self.supply.save()
        self.supply = Fabric.create(**base_fabric)
    
   
