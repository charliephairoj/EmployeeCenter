"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import random

from django.test import TestCase
from django.contrib.auth.models import User, Permission
from django.conf import settings

from products.models import Product, Model, Configuration, Upholstery, Table, Pillow
from auth.models import S3Object

base_product = {"width": 1000, 
                "depth": 500,
                "height": 400,
                "wholesale_price": 100000,
                "retail_price": 250000,
                "manufacture_price": 50000,
                "export_price": 100000,
                "back_pillow": 1,
                "accent_pillow": 2,
                "lumbar_pillow": 3,
                "corner_pillow": 4}
base_model = {"model": "AC-1",
              "name": "Susie",
              "collection": "Dellarobbia Thailand"}
base_configuration = {"configuration": "Sofa"}
base_upholstery = {"model": {"id": 1},
                   "configuration": {"id": 1}}
base_upholstery.update(base_product)
base_table = {"model": {"id": 1},
              "configuration": {"id": 1}}
base_table.update(base_product)


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


class ProductTest(TestCase):
    """
    Tests the Product Class
    """
    def setUp(self):
        self.user = create_user()
        self.test_image = S3Object.create("{0}test.jpg".format(settings.MEDIA_ROOT),
                                          "test{0}".format(random.randint(1, 100000)),
                                          "media.dellarobbiathailand.com",
                                          delete_original=False)
        product_data = base_product.copy()
        product_data["image"] = {"id": self.test_image.id}
        self.product = Product.create(user=self.user, **product_data)
        
    def test_create_product(self):
        """
        Tests creating a product
        """
        self.assertIsInstance(self.product, Product)
        self.assertIsNotNone(self.product.id, Product)
        self.assertEqual(self.product.width, 1000)
        self.assertEqual(self.product.depth, 500)
        self.assertEqual(self.product.height, 400)
        self.assertEqual(self.product.retail_price, 250000)
        self.assertEqual(self.product.wholesale_price, 100000)
        self.assertEqual(self.product.export_price, 100000)
        self.assertEqual(self.product.manufacture_price, 50000)
        self.assertIsInstance(self.product.image, S3Object)
        self.assertEqual(self.product.image, self.test_image)

    def test_update_product(self):
        self._update_with_basic_user()
        self._update_with_user_with_powers()

    def _update_with_basic_user(self):
        """
        Tests whether price can be updated when user lacks permissions
        """
        #blocked retail price
        blocked_permissions = ["edit_retail_price"]
        user = create_user(blocked_permissions)
        self.product.update(user=user, retail_price=100)
        self.assertEqual(self.product.retail_price, 250000)

        #blocked wholesale price
        blocked_permissions = ["edit_wholesale_price"]
        user = create_user(blocked_permissions)
        self.product.update(user=user, wholesale_price=200)
        self.assertEqual(self.product.wholesale_price, 100000)

        #blocked export price
        blocked_permissions = ["edit_export_price"]
        user = create_user(blocked_permissions)
        self.product.update(user=user, export_price=300)
        self.assertEqual(self.product.export_price, 100000)

        #blocked manufacture price
        blocked_permissions = ["edit_manufacture_price"]
        user = create_user(blocked_permissions)
        self.product.update(user=user, manufacture_price=400)
        self.assertEqual(self.product.manufacture_price, 50000)

    def _update_with_user_with_powers(self):
        """
        Updates the product when user has permission
        """
        #blocked retail price
        blocked_permissions = ["edit_wholesale_price",
                               "edit_export_price",
                               "edit_manufacture_price"]
        user = create_user(blocked_permissions)
        self.product.update(user=user, retail_price=100)
        self.assertEqual(self.product.retail_price, 100)

        #blocked wholesale price
        blocked_permissions = ["edit_retail_price",
                               "edit_export_price",
                               "edit_manufacture_price"]
        user = create_user(blocked_permissions)
        self.product.update(user=user, wholesale_price=200)
        self.assertEqual(self.product.wholesale_price, 200)

        #blocked export price
        blocked_permissions = ["edit_retail_price",
                               "edit_wholesale_price",
                               "edit_manufacture_price"]
        user = create_user(blocked_permissions)
        self.product.update(user=user, export_price=300)
        self.assertEqual(self.product.export_price, 300)

        #blocked manufacture price
        blocked_permissions = ["edit_retail_price",
                               "edit_wholesale_price",
                               "edit_export_price"]
        user = create_user(blocked_permissions)
        self.product.update(user=user, manufacture_price=400)
        self.assertEqual(self.product.manufacture_price, 400)

    def test_to_dict(self):
        data = self.product.to_dict(user=self.user)
        self.assertIn("retail_price", data)
        self.assertIn("wholesale_price", data)
        self.assertIn("export_price", data)
        self.assertIn("manufacture_price", data)
        self.assertIn("width", data)
        self.assertEqual(data["width"], 1000)
        self.assertIn("depth", data)
        self.assertEqual(data["depth"], 500)
        self.assertIn("height", data)
        self.assertEqual(data["height"], 400)
        self.assertEqual(self.product.pillow_set.get(type="back").quantity, 1)
        self.assertEqual(self.product.pillow_set.get(type="accent").quantity, 2)
        self.assertEqual(self.product.pillow_set.get(type="lumbar").quantity, 3)
        self.assertEqual(self.product.pillow_set.get(type="corner").quantity, 4)

        #blocked retail price
        blocked_permissions = ["view_retail_price"]
        user = create_user(blocked_permissions)
        data = self.product.to_dict(user=user)
        self.assertNotIn("reatil_price", data)

        #blocked wholesale price
        blocked_permissions = ["view_wholesale_price"]
        user = create_user(blocked_permissions)
        data = self.product.to_dict(user=user)
        self.assertNotIn("wholesale_price", data)

        #blocked export price
        blocked_permissions = ["view_export_price"]
        user = create_user(blocked_permissions)
        data = self.product.to_dict(user=user)
        self.assertNotIn("export_price", data)

        #blocked manufacture price
        blocked_permissions = ["view_manufacture_price"]
        user = create_user(blocked_permissions)
        data = self.product.to_dict(user=user)
        self.assertNotIn("manufacture_price", data)

    def tearDown(self):
        self.product.image.delete()


class ModelTest(TestCase):
    def setUp(self):
        """
        Setup for tests
        """
        self.model = Model.create(**base_model)
        
    def test_create_model(self):
        """
        Tests creating a model
        """
        self.assertIsInstance(self.model, Model)
        self.assertEqual(self.model.model, "AC-1")
        self.assertEqual(self.model.name, "Susie")
        self.assertEqual(self.model.collection, "Dellarobbia Thailand")


class ConfigurationTest(TestCase):
    def setUp(self):
        self.configuration = Configuration.create(**base_configuration)

    def test_create_configuration(self):
        """
        Tests creating a new configuration
        """
        self.assertIsInstance(self.configuration, Configuration)
        self.assertEqual(self.configuration.configuration, "Sofa")


class UpholsteryTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.model = Model.create(**base_model)
        self.configuration = Configuration.create(**base_configuration)
        self.upholstery = Upholstery.create(user=self.user, **base_upholstery)

    def test_create_upholstery(self):
        """
        Tests creating a new upholstery
        """
        self.assertIsInstance(self.upholstery, Upholstery)
        self.assertTrue(issubclass(Upholstery, Product))
        self.assertIsInstance(self.upholstery.model, Model)
        self.assertEqual(self.upholstery.model.id, 1)
        self.assertIsInstance(self.upholstery.configuration, Configuration)
        self.assertEqual(self.upholstery.configuration.id, 1)
        self.assertEqual(self.upholstery.type, "upholstery")
        self.assertEqual(self.upholstery.description, "AC-1 Sofa")

        #Parent attributes
        self.assertEqual(self.upholstery.width, 1000)
        self.assertEqual(self.upholstery.depth, 500)
        self.assertEqual(self.upholstery.height, 400)
        self.assertEqual(self.upholstery.retail_price, 250000)
        self.assertEqual(self.upholstery.wholesale_price, 100000)
        self.assertEqual(self.upholstery.export_price, 100000)
        self.assertEqual(self.upholstery.manufacture_price, 50000)

    def test_update_upholstery(self):
        """
        Tests updating the upholstery
        """
        self.upholstery.update(width=1200, depth=600, height=500)
        self.assertEqual(self.upholstery.width, 1200)
        self.assertEqual(self.upholstery.depth, 600)
        self.assertEqual(self.upholstery.height, 500)

        #update prices with no rights user
        user = create_user(["edit_wholesale_price",
                            "edit_retail_price",
                            "edit_export_price",
                            "edit_manufacture_price"])
        self.upholstery.update(user=user, retail_price=300000)
        self.assertEqual(self.upholstery.retail_price, 250000)
        self.upholstery.update(user=user, wholesale_price=150000)
        self.assertEqual(self.upholstery.wholesale_price, 100000)
        self.upholstery.update(user=user, export_price=150000)
        self.assertEqual(self.upholstery.export_price, 100000)
        self.upholstery.update(user=user, manufacture_price=75000)
        self.assertEqual(self.upholstery.manufacture_price, 50000)

        #Update prices with full rights user
        full_rights_user = create_user()
        self.upholstery.update(user=full_rights_user, retail_price=300000)
        self.assertEqual(self.upholstery.retail_price, 300000)
        self.upholstery.update(user=full_rights_user, wholesale_price=150000)
        self.assertEqual(self.upholstery.wholesale_price, 150000)
        self.upholstery.update(user=full_rights_user, export_price=125000)
        self.assertEqual(self.upholstery.export_price, 125000)
        self.upholstery.update(user=full_rights_user, manufacture_price=75000)
        self.assertEqual(self.upholstery.manufacture_price, 75000)


class TableTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.model = Model.create(**base_model)
        config_data = {"configuration": "Table"}
        self.configuration = Configuration.create(**config_data)
        self.table = Table.create(user=self.user, **base_table)

    def test_create_table(self):
        """
        Tests creating a new table
        """
        self.assertIsInstance(self.table, Table)
        self.assertTrue(issubclass(Table, Product))
        self.assertIsInstance(self.table.model, Model)
        self.assertEqual(self.table.model.id, 1)
        self.assertIsInstance(self.table.configuration, Configuration)
        self.assertEqual(self.table.configuration.id, 1)
        self.assertEqual(self.table.type, "table")
        self.assertEqual(self.table.description, "AC-1 Table")

        #Parent Attributes
        self.assertEqual(self.table.width, 1000)
        self.assertEqual(self.table.depth, 500)
        self.assertEqual(self.table.height, 400)
        self.assertEqual(self.table.retail_price, 250000)
        self.assertEqual(self.table.wholesale_price, 100000)
        self.assertEqual(self.table.export_price, 100000)
        self.assertEqual(self.table.manufacture_price, 50000)

    def test_update_table(self):
        """
        Tests updating the table
        """
        self.table.update(width=1200, depth=600, height=500)
        self.assertEqual(self.table.width, 1200)
        self.assertEqual(self.table.depth, 600)
        self.assertEqual(self.table.height, 500)

        #update prices with no rights user
        user = create_user(["edit_wholesale_price",
                            "edit_retail_price",
                            "edit_export_price",
                            "edit_manufacture_price"])
        self.table.update(user=user, retail_price=300000)
        self.assertEqual(self.table.retail_price, 250000)
        self.table.update(user=user, wholesale_price=150000)
        self.assertEqual(self.table.wholesale_price, 100000)
        self.table.update(user=user, export_price=150000)
        self.assertEqual(self.table.export_price, 100000)
        self.table.update(user=user, manufacture_price=75000)
        self.assertEqual(self.table.manufacture_price, 50000)

        #Update prices with full rights user
        full_rights_user = create_user()
        self.table.update(user=full_rights_user, retail_price=300000)
        self.assertEqual(self.table.retail_price, 300000)
        self.table.update(user=full_rights_user, wholesale_price=150000)
        self.assertEqual(self.table.wholesale_price, 150000)
        self.table.update(user=full_rights_user, export_price=125000)
        self.assertEqual(self.table.export_price, 125000)
        self.table.update(user=full_rights_user, manufacture_price=75000)
        self.assertEqual(self.table.manufacture_price, 75000)
