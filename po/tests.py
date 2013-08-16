"""
Purchase Order tests
"""
import random
import dateutil.parser
import datetime
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User, Permission

from contacts.models import Supplier
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
                 'address': base_address,
                 'terms': 30}

base_fabric = {'pattern': 'Maxx',
               'color': 'Blue',
               'quantity': 10,
               'reference': 'A1',
               'supplier': {'id': 1},
               'unit_cost': 12.11}

base_purchase_order = {'supplier': {'id':1},
                       'supplies': [{'id': 1, 'quantity':10}],
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


class PurchaseOrderTest(TestCase):
    """
    Tests the Purchase Order
    """
    def setUp(self):
        """
        Set up dependent objects
        """
        self.supplier = Supplier.create(**base_supplier)
        self.supply = Fabric.create(**base_fabric)
        self.user = create_user()
        
        #Tests dependencies are created
        self.assertIsNotNone(self.supplier)
        self.assertIsInstance(self.supplier, Supplier)
        self.assertIsNotNone(self.supply)
        self.assertIsInstance(self.supply, Supply)
        self.assertIsNotNone(self.user)
        self.assertIsInstance(self.user, User)
    
    def test_create_po(self):
        """
        Tests creating the po
        """
        self.po = PurchaseOrder.create(user=self.user,
                                       **base_purchase_order)
        self.assertIsNotNone(self.po)
        self.assertIsInstance(self.po, PurchaseOrder)
        
        #Test po vars
        self.assertEqual(self.po.currency, 'THB')
        self.assertEqual(self.po.terms, 30)
        #Tests order values
        self.assertEqual(self.po.vat, 7)
        self.assertEqual(round(self.po.grand_total, 2), 129.58)
        self.assertEqual(len(self.po.item_set.all()), 1)
        
    def test_create_po_with_discount(self):
        """
        Tests creating a po with a discount
        """
        order = base_purchase_order.copy()
        order['discount'] = 30
        self.po = PurchaseOrder.create(user=self.user,
                                       **order)
        
        self.assertIsNotNone(self.po)
        self.assertIsInstance(self.po, PurchaseOrder)
        
        #Tests values
        self.assertEqual(self.po.discount, 30)
        self.assertEqual(self.po.vat, 7)
        self.assertEqual(round(self.po.subtotal, 2), 121.10)
        self.assertEqual(round(self.po.total, 2), 84.77)
        self.assertEqual(round(self.po.grand_total, 2), 90.70)
        
    def test_update_receive_date(self):
        """
        Tests updating the recieve date of the po
        """
        self.po = PurchaseOrder.create(user=self.user,
                                       **base_purchase_order)
        self.po.update(receive_date=date)
        
        self.assertIsNotNone(self.po.receive_date)
        self.assertIsInstance(self.po.receive_date, datetime.datetime)
        self.assertEqual(self.po.receive_date, date)
        

class ItemTest(TestCase):
    """
    Tests the PO Item
    """
    def setUp(self):
        self.supplier = Supplier.create(**base_supplier)
        self.supply = Fabric.create(**base_fabric)
    
    def test_create_item(self):
        self.item = Item.create(id=1, quantity=2)
        self.assertIsNotNone(self.item)
        self.assertIsInstance(self.item, Item)
        self.assertEqual(round(self.item.unit_cost, 2), 12.11)
        self.assertEqual(round(self.item.total, 2), 24.22)
