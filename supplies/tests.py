"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from decimal import Decimal
import random
import json

from django.conf import settings
from django.test import TestCase
from django.contrib.auth.models import User, Permission

from contacts.models import Supplier
from supplies.models import Supply, Fabric, Foam, SupplyLog
from auth.models import S3Object


base_supplier = {"name": "Test Supplier",
                 "currency": "USD",
                 "address": {"address1": "22471 Sunbroon",
                             "city": "Mission Viejo",
                             "territory": "CA",
                             "country": "USA",
                             "zipcode": "92839"}}

base_supply = {"description": "test",
               "width": 100,
               "depth": 200,
               "height": 300,
               "purchasing_units": "ml",
               "reference": "A2234",
               "cost": 100,
               "quantity": 10.8,
               "supplier": {"id": 1}}

base_fabric = base_supply.copy()
base_fabric.update({"pattern": "Max",
                    "color": "Hot Pink"})


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


class SupplyTest(TestCase):
    def setUp(self):
        self.supplier = Supplier.create(**base_supplier)
        self.test_image = S3Object.create("{0}test.jpg".format(settings.MEDIA_ROOT),
                                          "test{0}".format(random.randint(1, 100000)),
                                          "media.dellarobbiathailand.com",
                                          delete_original=False)
        supply_data = base_supply.copy()
        supply_data["image"] = {"id": self.test_image.id}
        self.supply = Supply.create(**supply_data)
        self.user = create_user()

    def test_create_supply(self):
        self.assertIsInstance(self.supply, Supply)
        self.assertEqual(self.supply.description, 'test')
        self.assertEqual(self.supply.width, 100)
        self.assertEqual(self.supply.depth, 200)
        self.assertEqual(self.supply.height, 300)
        self.assertEqual(self.supply.purchasing_units, 'ml')
        self.assertEqual(self.supply.cost, 100)
        self.assertEqual(self.supply.quantity, Decimal('10.8'))
        self.assertEqual(self.supply.reference, "A2234")
        self.assertIsNotNone(self.supply.image)
        self.assertIsInstance(self.supply.image, S3Object)

    def test_create_supply_with_alt_units(self):
        """
        Tests creating supply with different units
        """
        supply_data = base_supply.copy()
        supply_data["width_units"] = "ml"
        supply_data["depth_units"] = "cm"
        supply_data["height_units"] = "m"
        supply_data["quantity_units"] = "pc"
        supply_data["purchasing_units"] = "km"
        supply = Supply.create(**supply_data)

        self.assertEqual(supply.width_units, "ml")
        self.assertEqual(supply.depth_units, "cm")
        self.assertEqual(supply.height_units, "m")
        self.assertEqual(supply.quantity_units, "pc")
        self.assertEqual(supply.purchasing_units, "km")

    def test_invalid_create(self):
        """
        Tests creating a supply with invalid data
        """
        #Dimensions
        #self.assertRaises(AttributeError, lambda: Supply.create(**self._get_modified_data(base_supply, "width")))
        #self.assertRaises(AttributeError, lambda: Supply.create(**self._get_modified_data(base_supply, "depth")))
        #self.assertRaises(AttributeError, lambda: Supply.create(**self._get_modified_data(base_supply, "height")))

        #Quantity
        #self.assertRaises(AttributeError, lambda: Supply.create(**self._get_modified_data(base_supply, "quantity")))

        #Reference
        #self.assertRaises(AttributeError, lambda: Supply.create(**self._get_modified_data(base_supply, "reference")))

    def test_update_supply(self):
        """
        Tests updating the supply
        """
        #Dimensions
        self.supply.update(width=1000)
        self.assertEqual(self.supply.width, 1000)
        self.supply.update(depth=1100)
        self.assertEqual(self.supply.depth, 1100)
        self.supply.update(height=1200)
        self.assertEqual(self.supply.height, 1200)

        #quantity
        self.supply.update(quantity=9)
        self.assertEqual(self.supply.quantity, 9)

        #cost
        self.supply.update(cost=111)
        self.assertEqual(self.supply.cost, 111)
        self.supply.update(unit_cost=112)
        self.assertEqual(self.supply.cost, 112)

        #units
        self.supply.update(width_units="cm")
        self.assertEqual(self.supply.width_units, "cm")
        self.supply.update(depth_units="m")
        self.assertEqual(self.supply.depth_units, "m")
        self.supply.update(height_units="dm")
        self.assertEqual(self.supply.height_units, "dm")
        self.supply.update(quantity_units="ml")
        self.assertEqual(self.supply.quantity_units, "ml")
        self.supply.update(purchasing_units="pc")
        self.assertEqual(self.supply.purchasing_units, "pc")

        #image
        self.assertEqual(len(S3Object.objects.all()), 1)
        self.assertEqual(S3Object.objects.all()[0].key, self.supply.image.key)
        new_image = S3Object.create("{0}test.jpg".format(settings.MEDIA_ROOT),
                                    "new_test_image.jpg",
                                    "media.dellarobbiathailand.com",
                                    False)
        self.assertEqual(len(S3Object.objects.all()), 2)
        self.supply.update(image={"id": new_image.id})
        self.assertIsNotNone(self.supply.image)
        self.assertIsInstance(self.supply.image, S3Object)
        self.assertEqual(self.supply.image.key, "new_test_image.jpg")
        self.assertEqual(self.supply.image.id, 2)
        self.assertEqual(len(S3Object.objects.all()), 1)
        self.assertEqual(S3Object.objects.all()[0].key, "new_test_image.jpg")

    def test_add_supply(self):
        """
        Tests adding supply quantity
        """
        self.assertEqual(self.supply.quantity, Decimal('10.8'))
        self.assertRaises(TypeError, lambda: self.supply.add(1))
        self.supply.add(1, self.user)
        self.assertEqual(self.supply.quantity, Decimal('11.8'))

        self._test_log("Added 1mm to test")

    def test_reserve_supply(self):
        """
        Tests reserving supply quantity
        """
        self.assertEqual(self.supply.quantity, Decimal('10.8'))
        self.assertRaises(TypeError, lambda: self.supply.reserve(5))
        self.supply.reserve(5, self.user)

        self._test_log("Reserved 5mm of test")

    def test_subtract_supply(self):
        """
        Tests subtracting supply quantity
        """
        self.assertEqual(self.supply.quantity, Decimal('10.8'))
        self.assertRaises(TypeError, lambda: self.supply.subtract(2))
        self.supply.subtract(3, self.user)
        self.assertEqual(self.supply.quantity, Decimal('7.8'))

        self._test_log("Subtracted 3mm from test")

    def test_reset_supply(self):
        """
        Tests resetting supply quantity
        """
        self.assertEqual(self.supply.quantity, Decimal('10.8'))
        self.assertRaises(TypeError, lambda: self.supply.reset(10))
        self.supply.reset(4.8, self.user)
        self.assertEqual(self.supply.quantity, Decimal('4.8'))

        self._test_log("Reset test to 4.8mm")

    def test_reserve_and_subtract(self):
        """
        Tests reserving and then subtracting a quantity
        """
        #Reserve
        self.assertEqual(self.supply.quantity, Decimal('10.8'))
        self.supply.reserve(2.3, self.user, acknowledgement_id=1120)
        self._test_log("Reserved 2.3mm of test")
        self.assertIsNotNone(SupplyLog.objects.get(event="Reserved 2.3mm of test"))

        #Subtract
        self.assertEqual(self.supply.quantity, Decimal('10.8'))
        self.supply.subtract(2.1, self.user, acknowledgement_id=1120)
        self.assertEqual(self.supply.quantity, Decimal('8.7'))
        self._test_log("Subtracted 2.1mm from test")
        self.assertRaises(SupplyLog.DoesNotExist, lambda: SupplyLog.objects.get(event="Reserved 2.3mm of test"))

    def _test_log(self, message, number_of_logs=1):
        """
        Tests the number of logs and the message of first log
        """
        self.assertEqual(len(SupplyLog.objects.all()), number_of_logs)
        self.assertEqual(SupplyLog.objects.all()[0].event, message)

    def _get_modified_data(self, data, delete_key=None):
        """
        Copies dictionary and deletes a specified keys
        """
        new_data = data.copy()
        if delete_key:
            del new_data[delete_key]
        return new_data

    def tearDown(self):
        """
        Stuff to do after each test
        """
        try:
            self.supply.image.delete()
        except ValueError as e:
            print e
     
            
class SupplyViewTest(TestCase):
    def setUp(self):
        """
        Set up the view 
        
        -login the user
        """
        
        User.objects.create_user('test', 'test', 'test')
        self.supplier = Supplier.create(**base_supplier)
        self.supply = Supply.create(**base_supply)
        self.supply2 = Supply.create(**base_supply)
        self.client.login(username='test', password='test')

    def test_get(self):
        """
        Tests that a standard get call works
        """
        
        #Testing standard GET
        response = self.client.get('/supply')
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(content), 2)
        self.assertIsNotNone(response.content)
        
        #Testing get with pk
        response = self.client.get('/supply/2')
        content = json.loads(response.content)
        self.assertEqual(reesponse.status_code, 200)
        self.assertIsNotNone(response.content)
        
    def test_post(self):
        """
        Tests posting to the server
        """
        response = self.client.post('/supply', base_supply)
        content = response.content
        self.assertEqual(response.status_code, 201)


class FabricTest(TestCase):
    def setUp(self):
        """
        Setups for tests
        """
        self.supplier = Supplier.create(**base_supplier)
        self.fabric = Fabric.create(**base_fabric)

    def test_create_fabric(self):
        """
        Tests creating a new fabric
        """
        self.assertIsInstance(self.fabric, Fabric)
        self.assertTrue(Fabric, Supply)
        self.assertEqual(self.fabric.pattern, "Max")
        self.assertEqual(self.fabric.color, "Hot Pink")

    def test_update_fabric(self):
        """
        Tests updating the fabric
        """
        self.fabric.update(pattern="Glen")
        self.assertEqual(self.fabric.pattern, "Glen")
        self.fabric.update(color="Brown")
        self.assertEqual(self.fabric.color, "Brown")