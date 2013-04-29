"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from datetime import datetime
import dateutil.parser

from django.test import TestCase

from acknowledgements.models import *
from contacts.models import Customer, Address
from django.contrib.auth.models import User
from products.models import Product


class AcknowledgementTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('test', 'test', 'test')
        self.user.is_staff = True
        self.user.save()
        self.customer = Customer(first_name="John", last_name="Smith", currency="USD")
        self.customer.save()
        self.address = Address(address1="Jiggle", contact=self.customer)
        self.address.save()
        self.product = Product(description="test", width=1000, height=320, depth=760,
                               retail_price=100000, wholesale_price=25000, type="upholstery")
        self.product.save()
        self.delivery_date = dateutil.parser.parse("2013-04-26T13:59:01.143Z")

    def test_create_acknowledgement(self):
        self.acknowledgement = Acknowledgement.create({'customer': {'id':1},
                                                       'delivery_date': self.delivery_date.isoformat(),
                                                       'products':[{'id':1,
                                                                    'quantity': 2}]}, self.user)
        self.assertIsInstance(self.acknowledgement.employee, User)
        self.assertIsInstance(self.customer, Customer)
        self.assertIsInstance(self.delivery_date, datetime)
        self.assertIsNotNone(self.acknowledgement.acknowledgement_key)
        self.assertIsNotNone(self.acknowledgement.production_key)
        self.assertEqual(self.acknowledgement.status, "ACKNOWLEDGED")


class ItemTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('test', 'test', 'test')
        self.user.is_staff = True
        self.user.save()
        self.customer = Customer(first_name="John", last_name="Smith", currency="USD", type="Retail")
        self.customer.save()
        self.address = Address(address1="Jiggle", contact=self.customer)
        self.address.save()
        self.product = Product(description="test", width=1000, height=320, depth=760,
                               retail_price=100000, wholesale_price=25000, type="upholstery")
        self.product.save()
        self.delivery_date = dateutil.parser.parse("2013-04-26T13:59:01.143Z")

        self.acknowledgement = Acknowledgement.create({'customer': {'id':1},
                                                       'delivery_date': self.delivery_date.isoformat(),
                                                       'products':[{'id':1,
                                                                    'quantity': 2}]}, self.user)
        self.item = Item.create({'id': 1, 'quantity': 2, 'is_custom_size':True, 'width': 1500,
                                 'height': 320, 'depth': 760}, self.acknowledgement)

    def test_create_item(self):
        self.assertIsNotNone(self.item.quantity)
        self.assertIsNotNone(self.item.id)
        self.assertEqual(self.item.quantity, 2)
        self.assertEqual(self.item.width, 1500)
        self.assertEqual(self.item.depth, 760)
        self.assertEqual(self.item.height, 320)

    def test_calculate_upchar(self):
        self.assertEqual(self.item._calculate_upcharge(90, 150, 10, 1), 10)
        self.assertEqual(self.item._calculate_upcharge(150, 150, 10, 1), 10)
        self.assertEqual(self.item._calculate_upcharge(160, 150, 10, 1), 11)
        self.assertEqual(self.item._calculate_upcharge(300, 150, 10, 1), 13)

    def test_custom_price(self):
        self.assertEqual(self.item.unit_price, 117000)
        self.item = Item.create({'id': 1, 'quantity': 2, 'is_custom_size':True, 'width': 1500,
                                 'height': 400, 'depth': 760}, self.acknowledgement)
        self.assertEqual(self.item.unit_price, 127000)
