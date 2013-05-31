from decimal import Decimal
from django.db import models


class Contact(models.Model):
    name = models.CharField(max_length=200)
    telephone = models.TextField()
    fax = models.TextField()
    email = models.CharField(max_length=200, null=True)
    is_supplier = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=False)
    currency = models.CharField(max_length=10, null=True)

    class Meta:
        ordering = ['name']

    def get_data(self, user=None):
        """
        Returns the information stored in the
        model. The information returned is depends
        on the permissions of the user
        """
        data = {'id': self.id,
                'name': self.name,
                'email': self.email,
                'telephone': self.telephone,
                'fax': self.fax,
                'isSupplier': self.is_supplier,
                'isCustomer': self.is_customer,
                'addresses': [],
                'currency': self.currency}

        for address in self.address_set.all():
            data['addresses'].append(address.get_data())

        return data

    def set_data(self, data, user=None):
        """
        Sets the information to be stored for the contact.
        The information that will be saved depends on the
        permissions of the user
        """
        if "name" in data:
            self.name = data["name"]
        if "email" in data:
            self.email = data["email"]
        if "telephone" in data:
            self.telephone = data["telephone"]
        if "fax" in data:
            self.fax = data["fax"]
        if "term" in data:
            self.term = data["term"]
        if "currency" in data:
            self.currency = data["currency"]

        self.save()

        if "address" in data:
            try:
                address = Address.objects.get(id=data["address"]["id"])
            except:
                try:
                    address = self.address_set.all()[0]
                except IndexError:
                    address = Address()
            address.set_data(data["address"])
            address.contact = self
            address.save()
        elif "addresses" in data:
            #Loop through address
            # and set data
            for address_data in data["addresses"]:
                try:
                    address = Address.objects.get(id=address_data["id"])
                except:
                    address = Address()
                address.set_data(address_data)
                address.contact = self
                address.save()


class Address(models.Model):
    address1 = models.CharField(max_length=160, null=True)
    address2 = models.CharField(max_length=160, null=True)
    city = models.CharField(max_length=100, null=True)
    territory = models.CharField(max_length=150, null=True)
    country = models.CharField(max_length=150, null=True)
    zipcode = models.TextField(null=True)
    contact = models.ForeignKey(Contact)
    latitude = models.DecimalField(decimal_places=6, max_digits=9, null=True)
    longitude = models.DecimalField(decimal_places=6, max_digits=9, null=True)

    def get_data(self):
        #Structure data
        data = {'id': self.id,
                'address1': self.address1,
                'address2': self.address2,
                'city': self.city,
                'territory': self.territory,
                'country': self.country,
                'zipcode': self.zipcode}

        """We convert to string before float from Decimal in
        order to accomodate python pre 2.7"""
        if self.latitude != None:
            data.update({'lat': float(str(self.latitude))})
        if self.longitude != None:
            data.update({'lng': float(str(self.longitude))})
        #Return Data
        return data

    def set_data(self, data):
        if "address1" in data:
            self.address1 = data["address1"]
        if "address2" in data:
            self.address2 = data["address2"]
        if "city" in data:
            self.city = data["city"]
        if "territory" in data:
            self.territory = data["territory"]
        if "country" in data:
            self.country = data["country"]
        if "zipcode" in data:
            self.zipcode = data["zipcode"]
        """We have to change to str before decimal from float in order
        to accomodate python pre 2.7"""
        if "lat" in data:
            self.latitude = Decimal(str(data['lat']))
        if "lng" in data:
            self.longitude = Decimal(str(data['lng']))


class Customer(Contact):
    first_name = models.TextField()
    last_name = models.TextField()
    type = models.CharField(max_length=10, default="Retail")

    class Meta:
        ordering = ['name']

    def get_data(self, user=None):
        data = {'type': self.type,
                'first_name': self.first_name,
                'last_name': self.last_name}
        #Get parent data
        data.update(super(Customer, self).get_data(user=None))
        #Return data
        return data

    def set_data(self, data, user=None):
        self.is_customer = True
        if "type" in data:
            self.type = data["type"]
        if "first_name" in data:
            self.first_name = data["first_name"]
        if "last_name" in data:
            self.last_name = data["last_name"]
        try:
            self.name = "{0} {1}".format(self.first_name, self.last_name)
        except:
            self.name = self.first_name
        #Set parent data
        super(Customer, self).set_data(data, user=None)


class Supplier(Contact):
    terms = models.IntegerField(default=0)
    discount = models.IntegerField(default=0)

    #get data
    def get_data(self, user=None):
        #Structure data
        data = {'terms': self.terms,
                'discount': self.discount,
                'contacts': []}

        #Update with Parent data
        data.update(super(Supplier, self).get_data(user=user))
        #Add address dict and remove
        # the addresses dic

        if len(data['addresses']) > 0:
            data['address'] = data['addresses'][0]
            data.pop('addresses')
        #get supplier contacts
        for supplierContact in self.suppliercontact_set.all():
            data['contacts'].append(supplierContact.get_data())
        #returns the data
        return data

    #set data
    def set_data(self, data, user=None, employee=None):
        #set parent data
        super(Supplier, self).set_data(data)
        #set supplier data
        if "discount" in data:
            self.discount = data["discount"]
        if "terms" in data:
            self.terms = data['terms']
        self.is_supplier = True
        #save self
        self.save()
        #Add supplier contacts
        if "contacts" in data:
            for contact_data in data["contacts"]:
                if "id" in contact_data:
                    contact = SupplierContact.objects.get(id=contact_data['id'])
                else:
                    contact = SupplierContact()
                #sets the details and save
                contact.set_data(contact_data)
                contact.supplier = self
                contact.save()


class SupplierContact(models.Model):

    first_name = models.TextField()
    last_name = models.TextField()
    email = models.TextField()
    telephone = models.TextField()
    supplier = models.ForeignKey(Supplier)

    def get_data(self, user=None):
        #Stucture data
        data = {'id': self.id,
                'firstName': self.first_name,
                'lastName': self.last_name,
                'email': self.email,
                'telephone': self.telephone}
        #Return data
        return data

    def set_data(self, data, user=None):
        #Set data
        if "firstName" in data:
            self.first_name = data["firstName"]
        if "lastName" in data:
            self.last_name = data["lastName"]
        if "email" in data:
            self.email = data["email"]
        if "telephone" in data:
            self.telephone = data["telephone"]


