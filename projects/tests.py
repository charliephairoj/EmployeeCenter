"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase

from contacts.models import Customer



class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)


class ProjectTest(TestCase):
    def setUp(self):
        self.customer = Customer(first_name="John", last_name="Smith", currency="THB")
        self.customer.save()

    def test_create_project(self):
        self.assertIsInstanct(self.project.customer, Customer)


class RoomTest(TestCase):
    def setUp(self):
        pass

    def test_create_room(self):
        pass


class ItemTest(TestCase):
    def setUp(self):
        pass

    def test_create_item(self):
        pass


