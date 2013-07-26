"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from datetime import datetime
from decimal import Decimal
import dateutil
import copy
import random

from django.test import TestCase
from django.contrib.auth.models import User, Permission

from acknowledgements.models import Acknowledgement, Item, Pillow
from supplies.models import Fabric
from contacts.models import Customer, Address, Supplier
from products.models import Product
from auth.models import S3Object

base_delivery_date = dateutil.parser.parse("2013-04-26T13:59:01.143Z")
base_customer = {'first_name': "John",
                 "last_name": "Smith",
                 "type": "Dealer",
                 "currency": "USD"}
base_supplier = {"name": "Test Supplier",
                 "id": 1,
                 "currency": "THB"}
base_fabric = {"pattern": "Max",
               "color": "charcoal",
               "reference": "A-2323",
               "quantity": 0,
               "unit_cost": 1.22,
               "supplier": {"id": 1}}
base_product = {"description": "test1",
                "width": 1000,
                "height": 320,
                "depth": 760,
                "retail_price": 100000,
                "wholesale_price": 25000,
                "type": "upholstery",
                "collection": "Dellarobbia Thailand",
                "back_pillow": 4,
                "accent_pillow": 3,
                "id": 1}
base_ack = {'customer': {'id': 1},
            'po_id': '123-213-231',
            'vat': 0,
            'delivery_date': base_delivery_date.isoformat(),
            'products': [{'id': 1,
                          'quantity': 2,
                          'fabric': {"id": 1},
                          'pillows':[{"type": "back",
                                      "fabric": {"id": 1}},
                                      {"type": "back",
                                       "fabric": {"id": 2}},
                                     {"type": "back",
                                      "fabric": {"id": 1}},
                                     {"type": "accent",
                                      "fabric": {"id": 2}},
                                     {"type": "accent"}]},
                         {'id': 1,
                          'quantity': 1,
                          'is_custom_size': True,
                          'width': 1500,
                          "fabric": {"id":1}}]}


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


class AcknowledgementTest(TestCase):
    def setUp(self):
        """
        Set up for the Acknowledgement Test

        Objects created:
        -User
        -Customer
        -Supplier
        -Address
        -product
        -2 fabrics

        After Creating all the needed objects for the Acknowledgement, 
        test that all the objects have been made.
        """
        self.user = create_user()
        self.customer = Customer(**base_customer)
        self.customer.save()
        self.supplier = Supplier(**base_supplier)
        self.supplier.save()
        self.address = Address(address1="Jiggle", contact=self.customer)
        self.address.save()
        self.product = Product.create(self.user, **base_product)
        self.product.save()
        self.fabric = Fabric.create(**base_fabric)
        f_data = base_fabric.copy()
        f_data["pattern"] = "Stripe"
        self.fabric2 = Fabric.create(**f_data)

        self.assertIsNotNone(self.customer.id)
        self.assertIsNotNone(self.supplier.id)
        self.assertIsNotNone(self.address.id)
        self.assertIsNotNone(self.product.id)
        self.assertIsNotNone(self.fabric)
        self.assertIsNotNone(self.fabric2.id)

    def test_create_standard_acknowledgement(self):
        """
        Tests creating a standard acknowledgemnt with standard prices

        Creates using the base ack data.

        We test when the basic order details, then pdf details,
        the products, then the totals.
        """
        acknowledgement = Acknowledgement.create(self.user, **base_ack)
        self._test_basic_order_details(acknowledgement)
        self._test_pdf_details(acknowledgement)

        #products
        self.assertGreater(len(acknowledgement.item_set.all()), 0)
        self.assertEqual(len(acknowledgement.item_set.all()), 2)
        self.assertEqual(acknowledgement.item_set.all()[0].quantity, 2)
        self.assertEqual(acknowledgement.item_set.all()[1].quantity, 1)
        self.assertEqual(acknowledgement.item_set.all()[0].description,
                         "test1")
        self.assertEqual(acknowledgement.item_set.all()[1].description,
                         "test1")

        #Totals
        self.assertEqual(acknowledgement.subtotal, 79250)
        self.assertEqual(acknowledgement.total, 79250)

    def test_create_custom_price_acknowledgemet(self):
        """
        Tests creating a new acknowledgement with a custom priced item

        We expect that the total should be the same as the stamdard acknowledgement
        test except the price will increase by 100
        """
        ack = copy.deepcopy(base_ack)
        ack["products"].append({"id": 1,
                                "quantity": 1,
                                "is_custom_size": True,
                                "width": 1500,
                                "depth": 0,
                                "height": 600,
                                "custom_price": 100})

        acknowledgement = Acknowledgement.create(self.user, **ack)
        self._test_basic_order_details(acknowledgement)
        self._test_pdf_details(acknowledgement)

        #Totals
        self.assertEqual(acknowledgement.subtotal, 79350)
        self.assertEqual(acknowledgement.total, 79350)

    def _test_basic_order_details(self, acknowledgement):
        self.assertIsInstance(acknowledgement.employee, User)
        self.assertIsInstance(acknowledgement.customer, Customer)
        self.assertIsInstance(acknowledgement.delivery_date, datetime)
        self.assertEqual(acknowledgement.status, "ACKNOWLEDGED")
        self.assertIsInstance(acknowledgement.time_created, datetime)

    def _test_pdf_details(self, acknowledgement):
        """
        Tests the PDF details
        """
        self.assertIsNotNone(acknowledgement.acknowledgement_pdf)
        self.assertIsNotNone(acknowledgement.production_pdf)
        self.assertIsNotNone(acknowledgement.original_acknowledgement_pdf)
        self.assertIsInstance(acknowledgement.acknowledgement_pdf, S3Object)
        self.assertIsInstance(acknowledgement.production_pdf, S3Object)
        self.assertIsInstance(acknowledgement.original_acknowledgement_pdf, S3Object)


class ItemTest(TestCase):
    def setUp(self):
        """
        Sets up for the item test
        """
        self.user = create_user()
        self.customer = Customer(first_name="John",
                                 last_name="Smith",
                                 currency="USD",
                                 type="Dealer")
        self.customer.save()
        self.address = Address(address1="Jiggle", contact=self.customer)
        self.address.save()
        self.product = Product.create(self.user, **base_product)
        self.product.save()
        self.delivery_date = dateutil.parser.parse("2013-04-26T13:59:01.143Z")
        self.supplier = Supplier(**base_supplier)
        self.supplier.save()
        self.fabric1 = Fabric.create(**base_fabric)
        self.fabric2 = Fabric.create(**base_fabric)
        ack = base_ack.copy()
        ack["products"] = []

        self.acknowledgement = Acknowledgement.create(self.user, **ack)
        item_d = {'id': 1,
                  'quantity': 2,
                  'is_custom_size': True,
                  'width': 1500,
                  'height': 320,
                  'depth': 760}
        self.item = Item.create(self.acknowledgement, **item_d)

    def test_create_item(self):
        """
        Tests that an item is correctly
        created
        """
        self.assertIsNotNone(self.item.quantity)
        self.assertIsNotNone(self.item.id)
        self.assertEqual(self.item.quantity, 2)
        self.assertEqual(self.item.width, 1500)
        self.assertEqual(self.item.depth, 760)
        self.assertEqual(self.item.height, 320)

    def test_create_incomplete_dimension_item(self):
        """
        Tests that a item is correctly created
        if it is missing a dimensions, or a dimensions
        is None.
        """
        item_d = {'id': 1,
                  'quantity': 1,
                  'is_custom_size': True,
                  'width': 1750,
                  'height': None}

        item = Item.create(self.acknowledgement, **item_d)
        self.assertIsInstance(item, Item)
        self.assertEqual(item.width, 1750)
        self.assertEqual(item.depth, 760)
        self.assertEqual(item.height, 320)
        self.assertTrue(item.is_custom_size)

    def test_calculate_upcharge(self):
        """
        Tests that the item can correctly
        calculate the upcharge percentage
        for a custom sized item
        """
        self.assertEqual(self.item._calculate_upcharge(90, 150, 10, 1), 10)
        self.assertEqual(self.item._calculate_upcharge(150, 150, 10, 1), 10)
        self.assertEqual(self.item._calculate_upcharge(160, 150, 10, 1), 11)
        self.assertEqual(self.item._calculate_upcharge(300, 150, 10, 1), 13)

    def test_custom_price(self):
        """
        Tsts that an item can correctly calculate
        the price of a custom size item
        """
        self.assertEqual(self.item.unit_price, 29250)
        item_data = {'id': 1,
                     'quantity': 2,
                     'is_custom_size': True,
                     'width': 1500,
                     'height': 400,
                     'depth': 760,
                     'custom_price': 1}
        self.item = Item.create(self.acknowledgement, **item_data)
        self.assertEqual(self.item.unit_price, 1)

    def test_pillows(self):
        """
        Tests the the pillows are correctly
        created, with the correct fabric
        when an item is created
        """
        pillow_item_data = base_ack["products"][0].copy()
        self.item_pillow = Item.create(self.acknowledgement, **pillow_item_data)
        self.assertEqual(len(self.item_pillow.pillow_set.all()), 4)
        pillows = self.item.pillow_set.all()
        for pillow in pillows:
            self.assertNotNone(pillow.type)
            self.assertNotNone(pillow.quantity)
            self.assertIsInstance(pillow, Pillow)

            if pillow.fabric == None:
                self.assertEqual(pillow.quantity, 1)
            elif pillow.fabric.id == 1 and pillow.type == "back":
                self.assertEqual(pillow.quantity, 2)
            elif pillow.fabric.id == 2 and pillow.type == "back":
                self.assertEqual(pillow.quantiy, 1)
            elif pillow.fabric.id == 2 and pillow.type == "accent":
                self.assertEqual(pillow.quantity, 1)
            else:
                raise ValueError("Unexpected pillow")

    def test_missing_quantity(self):
        """
        Tests that an error is raised if
        an item with a missing quantity
        is created
        """
        item_data = {id: 1}
        self.assertRaises(ValueError, lambda: Item.create(item_data))
