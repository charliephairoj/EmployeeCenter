"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase

from contacts.models import Address, Contact, Customer, Supplier, SupplierContact


base_address = {"address1": "22471 Sunbrook",
                "city": "Mission Viejo",
                "territory": "CA",
                "country": "USA",
                "zipcode": 92692}
base_contact = {"name": "Charlie Brown",
                'first_name': 'Charlie',
                'last_name': 'Brown',
                "currency": "USD",
                "email": "charliep@dellarobbiathailand.com",
                "fax": "0224223423",
                "telephone": "08348229383"}
base_supplier_contact = {"contacts": [{"first_name": "Charlie",
                         "last_name": "Smith",
                         "email": "test@yahoo.com",\
                         
                         "telephone": "123456789"}]}


class AddressTest(TestCase):
    def setUp(self):
        contact = base_contact.copy()
        contact["address"] = base_address
        self.contact = Contact.create(**contact)
        self.address = Address.create(contact=self.contact, **base_address)

    def test_creaet_address(self):
        """
        Tests creating a new adderss
        """
        address = Address.create(contact=self.contact, **base_address)
        self.assertIsInstance(address, Address)

    def test_create_invalid_address(self):
        """
        Tests creating an address with invalid data
        """
        #Missing City
        address_data = base_address.copy()
        del address_data["city"]
        self.assertRaises(AttributeError, lambda: Address.create(contact=self.contact, **address_data))

        #Missing address
        address_data = base_address.copy()
        del address_data["address1"]
        self.assertRaises(AttributeError, lambda: Address.create(contact=self.contact, **address_data))

        #Missing territory
        address_data = base_address.copy()
        del address_data["territory"]
        self.assertRaises(AttributeError, lambda: Address.create(contact=self.contact, **address_data))

        #Missing country
        address_data = base_address.copy()
        del address_data["country"]
        self.assertRaises(AttributeError, lambda: Address.create(contact=self.contact, **address_data))

        #Missing zipcode
        address_data = base_address.copy()
        del address_data["zipcode"]
        self.assertRaises(AttributeError, lambda: Address.create(contact=self.contact, **address_data))

    def test_update_address(self):
        self.address.update({"address1": "8/10 Moo 4"})
        self.assertEqual(self.address.address1, "8/10 Moo 4")


class ContactTest(TestCase):
    def setUp(self):
        """
        Sets up for the tests
        """
        contact = base_contact.copy()
        contact["address"] = base_address
        self.contact = Contact.create(**contact)

    def test_create_contact(self):
        """
        Tests creating a contact
        """
        contact_data = base_contact.copy()
        contact_data["address"] = base_address
        contact = Contact.create(**contact_data)
        self.assertIsInstance(contact, Contact)
        self.assertEqual(contact.telephone, '08348229383')

    def test_create_contact_without_address(self):
        """
        Tests creating a contact without an address

        It should raise an error as all contacts must have at least 1 address
        """
        self.assertRaises(AttributeError, lambda: Contact.create(**base_contact))

    def test_add_address(self):
        """
        Tests adding an address to the contact
        """
        self.contact.update(**{'addresses': [base_address.copy()]})
        self.assertEqual(len(self.contact.address_set.all()), 2)


class CustomerTest(TestCase):
    def setUp(self):
        pass

    def test_create_customer(self):
        """
        Tests creating a new customer
        """
        customer_data = base_contact.copy()
        customer_data["address"] = base_address.copy()
        customer = Customer.create(**customer_data)
        self.assertIsInstance(customer, Customer)
        self.assertTrue(customer.is_customer)
        self.assertFalse(customer.is_supplier)
        self.assertEqual(customer.type, "Retail")
        
    def test_create_dealer(self):
        """
        Tests creating a new customer
        """
        customer_data = base_contact.copy()
        customer_data["address"] = base_address.copy()
        customer_data["type"] = "Dealer"
        customer = Customer.create(**customer_data)
        self.assertIsInstance(customer, Customer)
        self.assertTrue(customer.is_customer)
        self.assertFalse(customer.is_supplier)
        self.assertEqual(customer.type, 'Dealer')
        

    def test_create_customer_without_address(self):
        """
        Tests creating a new customer without an address
        """
        self.assertRaises(AttributeError, lambda: Customer.create(**base_contact))

        
class SupplierTest(TestCase):
    def setUp(self):
        supplier_data = base_contact.copy()
        supplier_data["addresses"] = [base_address.copy()]
        self.supplier = Supplier.create(**supplier_data)

    def test_create_supplier(self):
        """
        Tests creating a new supplier
        """
        supplier_data = base_contact.copy()
        supplier_data["addresses"] = [base_address.copy()]
        supplier = Supplier.create(**supplier_data)
        self.assertIsInstance(supplier, Supplier)
        self.assertTrue(supplier.is_supplier)
        self.assertFalse(supplier.is_customer)

    def test_create_supplier_without_address(self):
        """
        Tests creating a new supplier without an address
        """
        self.assertRaises(AttributeError, lambda: Supplier.create(**base_contact))

    def test_updating_supplier(self):
        #update discount
        self.supplier.update(discount=90)
        self.assertEqual(self.supplier.discount, 90)
        #update terms
        self.supplier.update(terms=30)
        self.assertEqual(self.supplier.terms, 30)
        #Change Name
        self.supplier.update(name="Zipper Land")
        self.assertEqual(self.supplier.name, "Zipper Land")

    def test_adding_contact_by_update(self):
        self.assertEqual(len(self.supplier.suppliercontact_set.all()), 0)
        self.supplier.update(**base_supplier_contact)
        self.assertEqual(len(self.supplier.suppliercontact_set.all()), 1)
        self.assertIsInstance(self.supplier.suppliercontact_set.all()[0], SupplierContact)
        self.supplier.suppliercontact_set.all().delete()

    def test_add_contact_by_fn(self):
        contact_data = base_supplier_contact["contacts"][0]
        self.assertEqual(len(self.supplier.suppliercontact_set.all()), 0)
        self.supplier.add_contact(**contact_data)
        self.assertEqual(len(self.supplier.suppliercontact_set.all()), 1)
        self.assertIsInstance(self.supplier.suppliercontact_set.all()[0], SupplierContact)
        self.supplier.suppliercontact_set.all().delete()

        
