from decimal import Decimal
from django.db import models


class Contact(models.Model):
    name = models.TextField()
    name_th = models.TextField()
    telephone = models.TextField()
    fax = models.TextField()
    email = models.CharField(max_length=200, null=True)
    is_supplier = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=False)
    discount = models.IntegerField(default=0)
    currency = models.CharField(max_length=10, null=True)
    notes = models.TextField(null=True)
    deleted = models.BooleanField(default=False)
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)
    
    #class Meta:
        #ordering = ['name']

    


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
    user_defined_latlng = models.BooleanField(default=False)
    
    @property
    def lat(self):
        return self.latitude
    
    @lat.setter
    def lat(self, latitude):
        self.latitude = latitude
        
    @property
    def lng(self):
        return self.longitude
    
    @lng.setter
    def lng(self, longitude):
        self.longitude = longitude
    
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


class Customer(Contact):
    first_name = models.TextField()
    last_name = models.TextField(null=True)
    type = models.CharField(max_length=10, default="Retail")

    #class Meta:
        #ordering = ['name']

    


class Supplier(Contact):
    terms = models.IntegerField(default=0)

    


class SupplierContact(models.Model):
    first_name = models.TextField()
    last_name = models.TextField()
    email = models.TextField()
    telephone = models.TextField()
    supplier = models.ForeignKey(Supplier)

    



