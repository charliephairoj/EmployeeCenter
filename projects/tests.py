"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import datetime
import dateutil

from django.conf import settings
from django.test import TestCase

from contacts.models import Customer
from products.models import Product, Model, Configuration, Upholstery
from projects.models import Project, Room, Item
from auth.models import S3Object

base_customer = {"first_name": "John",
                 "last_name": "Smith",
                 "currency": "THB",
                 "email": "test@yahoo.com",
                 "telephone": "ok",
                 "address": {"address1": "ok",
                             "city": "ok",
                             "territory": "ok",
                             "country": "thailand",
                             "zipcode": "9823-333"}}
product_data = {"width": 100,
                "depth": 100,
                "height": 100,
                "description": "Test Product"}
base_due_date = dateutil.parser.parse("2013-04-26T13:59:01.143Z")
base_project = {"reference": "S5",
                "address": {"address1": "8/10 Moo 4 Lam Lukka",
                            "city": "Lam Lukka",
                            "territory": "Pathum Thani",
                            "country": "Thailand",
                            "zipcode": "98233"},
                "customer": {"id": 1},
                "type": "Condominium",
                "due_date": base_due_date.isoformat(),
                "codename": "Haze"}
base_room = {"project": {"id": 1},
             "reference": "B-01",
             "description": "Master Bedroom"}
base_item = {"room": {"id": 1},
             "type": "Build-In",
             "reference": "F-01",
             "description": "TV Cabinet"}


class ProjectTest(TestCase):
    def setUp(self):
        """
        Sets up for tests
        """
        self.customer = Customer.create(**base_customer)
        self.project = Project.create(**base_project)

    def test_create_project(self):
        """
        Tests creating a project
        """
        self.assertIsNotNone(self.project)
        self.assertIsInstance(self.project, Project)
        self.assertIsInstance(self.project.customer, Customer)
        self.assertEqual(self.project.customer, self.customer)
        self.assertEqual(self.project.reference, "S5")
        self.assertEqual(self.project.type, "Condominium")
        self.assertEqual(self.project.due_date, base_due_date.date())
        self.assertEqual(self.project.codename, "Haze")

    def test_update_project(self):
        """
        Tests updating a project
        """
        self._update_due_date()
        self.project.update(reference="S9")
        self.assertEqual(self.project.reference, "S9")

    def _update_due_date(self):
        """
        Tests the updating of the due date
        """
        due_date = dateutil.parser.parse("2013-04-26T13:59:01.143Z")
        self.project.update(due_date=due_date.isoformat())
        self.assertEqual(self.project.due_date, due_date.date())
        delta = datetime.timedelta(days=5)
        due_date2 = due_date + delta
        self.project.update(due_date=due_date2)
        self.assertEqual(self.project.due_date, due_date2.date())


class RoomTest(TestCase):
    def setUp(self):
        """
        Sets up for tests
        """
        self.customer = Customer.create(**base_customer)
        self.project = Project.create(**base_project)
        self.room = Room.create(**base_room)

    def test_create_room(self):
        """
        Tests creating a room
        """
        self.assertIsNotNone(self.room)
        self.assertIsInstance(self.room, Room)
        self.assertIsInstance(self.room.project, Project)
        self.assertEqual(self.room.project, self.project)


class ItemTest(TestCase):
    def setUp(self):
        """
        Sets up for tests
        """
        self.customer = Customer.create(**base_customer)
        self.project = Project.create(**base_project)
        self.room = Room.create(**base_room)
        self.model = Model.create(model="AC-2010", name="Gloria", collection="Dellarobbia Thailand")
        self.configuration = Configuration.create(configuration="Sofa")
        uphol_data = product_data.copy()
        uphol_data["configuration"] = {"id": 1}
        uphol_data["model"] = {"id": 1}
        self.product = Upholstery.create(**uphol_data)
        
        #Regular item
        self.item = Item.create(**base_item)
        
        #Creates custom item
        custom_item_data = base_item.copy()
        custom_item_data["type"] = "Custom"
        custom_item_data["description"] = "Custom Product"
        custom_item_data["product"] = {"type": "upholstery",
                                "width": 100,
                                "depth": 200,
                                "height": 300,
                                "back_pillow": 1,
                                "model": {"id": 1},
                                "configuration": {"id": 1}}
        custom_item_data["reference"] = "F-02"
        self.custom_item = Item.create(**custom_item_data)

        #Creates product item
        product_item_data = base_item.copy()
        product_item_data["type"] = "Product"
        product_item_data["product"] = {"id": 1}
        product_item_data["reference"] = "F-01"
        self.product_item = Item.create(**product_item_data)
        
        #Creates build-in item
        item_data = base_item.copy()
        item_data["type"] = "Build-In"
        item_data["description"] = "TV Console"
        item_data["reference"] = "B-10"

        self.build_in_item = Item.create(**item_data)

    def test_create_item(self):
        """
        Tests creating an item
        """
        self._create_build_in_item()
        self._create_custom_item()
        self._create_product_item()

    def test_update_item(self):
        """
        Tests updating an item
        """
        #Due Date
        new_due_date = base_due_date + datetime.timedelta(days=3)
        self.item.update(due_date=new_due_date)
        self.assertEqual(self.item.due_date, new_due_date.date())

        #Delivery Date
        new_dd = base_due_date + datetime.timedelta(days=10)
        self.item.update(delivery_date=new_dd)
        self.assertEqual(self.item.delivery_date, new_dd.date())

    def test_invalid_update_custom_item(self):
        """
        Tests that an update fails with data
        """
        product_data = {"product": {"id": 1}}
        self.custom_item.update(product=product_data)
        self.assertEqual(self.custom_item.product.id, 2)
        self.assertNotEqual(self.custom_item, self.product)

    def _create_build_in_item(self):
        """
        Creates a build in item
        """
        self.assertIsInstance(self.build_in_item, Item)
        self.assertEqual(self.build_in_item.type, "Build-In")
        self.assertEqual(self.build_in_item.description, "TV Console")
        self.assertEqual(self.build_in_item.reference, "B-10")

    def _create_product_item(self):
        """
        Tests creating a product item
        """
        self.assertIsInstance(self.product_item, Item)
        self.assertEqual(self.product_item.type, "Product")
        self.assertEqual(self.product_item.description, "AC-2010 Sofa")
        self.assertIsInstance(self.product_item.product, Product)
        self.assertEqual(self.product_item.reference, "F-01")

    def _create_custom_item(self):
        """
        Tests Creates a custom item and the accompanying
        """
        #Test item
        self.assertIsInstance(self.custom_item, Item)
        self.assertEqual(self.custom_item.type, "Custom")
        self.assertEqual(self.custom_item.description, "S5 Sofa")
        self.assertEqual(self.custom_item.reference, "F-02")

        #Test item product
        self.assertIsInstance(self.custom_item.product, Product)
        self.assertEqual(self.custom_item.product.id, 2)
        self.assertEqual(self.custom_item.product.type.lower(), "upholstery")
        self.assertEqual(self.custom_item.product.width, 100)
        self.assertEqual(self.custom_item.product.depth, 200)
        self.assertEqual(self.custom_item.product.height, 300)
        self.assertEqual(len(self.custom_item.product.pillow_set.filter(type="back")), 1)

    def _update_custom_item(self):
        """
        Tests Updating a custom item
        """
        product_data = {"width": 1100,
                        "depth": 1200,
                        "height": 1300}
        self.custom_item.update(product=product_data)
        self.assertEqual(self.custom_item.width, 1100)
        self.assertEqual(self.custom_item.depth, 1200)
        self.assertEqual(self.custom_item.height, 1300)

