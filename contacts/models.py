from decimal import Decimal
from django.db import models


class Contact(models.Model):
    name = models.CharField(max_length=200)
    name_th = models.TextField()
    telephone = models.TextField()
    fax = models.TextField()
    email = models.CharField(max_length=200, null=True)
    is_supplier = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=False)
    currency = models.CharField(max_length=10, null=True)
    notes = models.TextField(null=True)
    deleted = models.BooleanField(default=False)
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)

    class Meta:
        ordering = ['name']

    @classmethod
    def create(cls, commit=True, **kwargs):
        """Creates a new Contact"""
        contact = cls()
        try:
            contact.name = kwargs["name"]["en"]
            if "th" in kwargs["name"]:
                contact.name_th = kwargs["name"]["th"]
        except (KeyError, TypeError):
            try:
                contact.name = kwargs["name"]
            except KeyError:
                contact.name = "{0} {1}".format(kwargs["first_name"], kwargs["last_name"])
       
        
        if "telephone" in kwargs:
            contact.telephone = kwargs["telephone"]
        if "fax" in kwargs:
            contact.fax = kwargs["fax"]
        if "email" in kwargs:
            contact.email = kwargs["email"]
        if "is_supplier" in kwargs:
            contact.is_supplier = kwargs["is_supplier"]
            contact.is_customer = kwargs["is_customer"]
        try:
            contact.currency = kwargs["currency"]
        except KeyError:
            raise AttributeError("Missing currency.")
        
        if "notes" in kwargs:
            contact.notes = kwargs["notes"]

        contact.save()

        if "address" in kwargs:
            address = Address.create(contact=contact, **kwargs["address"])
        elif "addresses" in kwargs:
            for address in kwargs["addresses"]:
                Address.create(contact=contact, **address)
        else:
            raise AttributeError("No address submitted")

        return contact

    def update(self, **kwargs):
        """
        Sets the information to be stored for the contact.
        The information that will be saved depends on the
        permissions of the user
        """
        if "name" in kwargs:
            self.name = kwargs["name"]
        if "email" in kwargs:
            self.email = kwargs["email"]
        if "telephone" in kwargs:
            self.telephone = kwargs["telephone"]
        if "fax" in kwargs:
            self.fax = kwargs["fax"]
        if "term" in kwargs:
            self.term = kwargs["term"]
        if "currency" in kwargs:
            self.currency = kwargs["currency"]
        self.save()

        if "address" in kwargs:
            try:
                address = Address.objects.get(id=kwargs["address"]["id"])
            except:
                try:
                    address = self.address_set.all()[0]
                except IndexError:
                    address = Address()
            address.update(kwargs["address"])
            address.contact = self
            address.save()
        elif "addresses" in kwargs:
            #Loop through address
            # and set data
            for address_data in kwargs["addresses"]:
                try:
                    Address.objects.get(id=address_data["id"]).update(**address_data)
                except:
                    Address.create(contact=self, **address_data)

    def to_dict(self, user=None):
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
                'currency': self.currency,
                "addresses": [address.to_dict() for address in self.address_set.all()]}
        return data


class Address(models.Model):
    address1 = models.CharField(max_length=160)
    address2 = models.CharField(max_length=160, null=True)
    city = models.CharField(max_length=100)
    territory = models.CharField(max_length=150)
    country = models.CharField(max_length=150)
    zipcode = models.TextField()
    contact = models.ForeignKey(Contact)
    latitude = models.DecimalField(decimal_places=6, max_digits=9, null=True)
    longitude = models.DecimalField(decimal_places=6, max_digits=9, null=True)

    @classmethod
    def create(cls, **kwargs):
        address = cls(**kwargs)

        if not address.address1:
            raise AttributeError("Missing 'address'")
        if not address.city:
            raise AttributeError("Missing 'city'")
        if not address.territory:
            raise AttributeError("Missing 'territory'")
        if not address.country:
            raise AttributeError("Missing 'country'")
        if not address.zipcode:
            raise AttributeError("Missing 'zipcode'")

        try:
            address.latitude = kwargs["lat"]
            address.longitude = kwargs["lng"]
        except:
            pass

        address.save()
        return address

    def update(self, data):
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
        self.save()

    def to_dict(self):
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
            data['lat'] = float(str(self.latitude))
        if self.longitude != None:
            data['lng'] = float(str(self.longitude))

        return data


class Customer(Contact):
    first_name = models.TextField()
    last_name = models.TextField()
    type = models.CharField(max_length=10, default="Retail")

    class Meta:
        ordering = ['name']

    @classmethod
    def create(cls, **kwargs):
        """
        Creates and returns a new customer
        """
        customer = super(Customer, cls).create(commit=False, **kwargs)
        
        if "type" in kwargs:
            customer.type = kwargs["type"]
            
        customer.is_customer = True
        customer.save()
        
        return customer

    def to_dict(self, user=None):
        data = {'type': self.type,
                'first_name': self.first_name,
                'last_name': self.last_name}
        #Get parent data
        data.update(super(Customer, self).to_dict(user=None))
        #Return data
        return data

    def update(self, data, user=None):
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
        super(Customer, self).update(data, user=None)


class Supplier(Contact):
    terms = models.IntegerField(default=0)
    discount = models.IntegerField(default=0)

    @classmethod
    def create(cls, **kwargs):
        """
        Creates and returns a new Customer object
        """
        supplier = super(Supplier, cls).create(commit=False, **kwargs)
        supplier.is_supplier = True
        
        if 'terms' in kwargs:
            supplier.terms = int(kwargs['terms'])
        
        if 'discount' in kwargs:
            supplier.discount = kwargs['discount']
        
        supplier.save()
        return supplier

    def update(self, **kwargs):
        """
        Updates the object's attributes
        """
        super(Supplier, self).update(**kwargs)
        #set supplier data
        if "discount" in kwargs:
            self.discount = kwargs["discount"]
        if "terms" in kwargs:
            self.terms = kwargs['terms']
        self.save()
        #Add supplier contacts
        if "contacts" in kwargs:
            for contact_data in kwargs["contacts"]:
                try:
                    contact = SupplierContact.objects.get(id=contact_data['id'])
                except KeyError, SupplierContact.DoesNotExist:
                    contact = SupplierContact.create(supplier=self, **contact_data)

    def to_dict(self, user=None):
        """
        Returns the object's attributes as a dictionary
        """
        data = {'terms': self.terms,
                'discount': self.discount,
                'contacts': [contact.to_dict() for contact in self.suppliercontact_set.all()]}

        data.update(super(Supplier, self).to_dict(user=user))

        if len(data['addresses']) > 0:
            data['address'] = data['addresses'][0]
            del data['addresses']

        return data

    def add_contact(self, **kwargs):
        """
        Creates a contact for the supplier and and associates it
        """
        self.suppliercontact_set.add(SupplierContact.create(supplier=self, **kwargs))


class SupplierContact(models.Model):
    first_name = models.TextField()
    last_name = models.TextField()
    email = models.TextField()
    telephone = models.TextField()
    supplier = models.ForeignKey(Supplier)

    @classmethod
    def create(cls, commit=True, **kwargs):
        sc = cls(**kwargs)
        if commit:
            sc.save()
        return sc

    def update(self, **kwargs):
        #Set data
        if "firstName" in kwargs:
            self.first_name = kwargs["firstName"]
        if "lastName" in kwargs:
            self.last_name = kwargs["lastName"]
        if "email" in kwargs:
            self.email = kwargs["email"]
        if "telephone" in kwargs:
            self.telephone = kwargs["telephone"]
        if "supplier" in kwargs:
            try:
                self.supplier = Supplier.objects.get(pk=kwargs["supplier"]["id"])
            except KeyError:
                print "Missing Supplier ID."
            except Supplier.DoesNotExist:
                print "Supplier does not exists."

    def to_dict(self, user=None):
        #Stucture data
        data = {'id': self.id,
                'firstName': self.first_name,
                'lastName': self.last_name,
                'email': self.email,
                'telephone': self.telephone}
        #Return data
        return data



