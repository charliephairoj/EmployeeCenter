from django.db import models
import logging

logger = logging.getLogger('EmployeeCenter');
# Create your models here.

#Creates the Contact Class
class Contact(models.Model):
    name = models.CharField(max_length=200)
    telephone = models.IntegerField()
    fax = models.IntegerField()
    email = models.CharField(max_length=200, null=True)
    isSupplier = models.BooleanField(default=False)
    isCustomer = models.BooleanField(default=False)
    
    
    def getData(self):
        
        #get all addresses
        addresses = [];
        #loop through all addresses
        for address in self.address_set.all():
            #temporary dict to hold address data
            temp = {
                    'id':address.id,
                    'address1':address.address1,
                    'address2':address.address2,
                    'city':address.city,
                    'territory':address.territory,
                    'country':address.country,
                    'zipcode':address.zipcode
                    }
            
            #add to address array
            addresses.append(temp)
        #set the 
        data = {
                'id':self.id,
                'name':self.name,
                'email':self.email,
                'telephone':self.telephone,
                'fax':self.fax,
                'isSupplier':self.isSupplier,
                'isCustomer':self.isCustomer,
                'addresses':addresses,
                
                }
        #returns the data
        return data
    
    def setData(self, data):
        if "name" in data: self.name = data["name"]
        if "email" in data: self.email = data["email"]
        if "telephone" in data: self.telephone = data["telephone"]
        if "fax" in data: self.fax = data["fax"]
        if "term" in data: self.term = data["term"]
       
        
        #save the contact
        self.save()
        
        #set address
        if "address" in data:
            address = Address()
            address.setData(data["address"])
            address.contact = self
            address.save()
        #set addresses
        if "addresses" in data:
            for dataset in data["addresses"]:
                address = Address()
                address.setData(dataset)
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
    
    
    
    def setData(self, data):
        if "address1" in data: self.address1 = data["address1"]
        if "address2" in data: self.address2 = data["address2"]
        if "city" in data: self.city = data["city"]
        if "territory" in data: self.territory = data["territory"]
        if "country" in data: self.country = data["country"]
        if "zipcode" in data: self.country = data["zipcode"]
    
#supplier class
class Supplier(Contact):
    terms = models.IntegerField(default=0)
    discount = models.IntegerField(default=0)
    #methods
    
    #get data
    def getData(self):
        
        
        #set the 
        data = {
                'id':self.id,
                'name':self.name,
                'email':self.email,
                'telephone':self.telephone,
                'fax':self.fax,
                'isSupplier':self.isSupplier,
                'isCustomer':self.isCustomer,
                'addressID':None,
                'address1':None,
                'address2':None,
                'city':None,
                'territory':None,
                'country':None,
                'zipcode':None,
                'terms':self.terms,
                'discount':self.discount
                }
        #sets address if exists
        if len(self.address_set.all())>0:
            address = self.address_set.all()[0]
            
            data["addressID"] = address.id
            data["address1"] = address.address1
            data["address2"] = address.address2
            data["city"] = address.city
            data["territory"] = address.territory
            data["country"] = address.country
            data["zipcode"] = address.zipcode
            
        #returns the data
        return data
    #set data
    def setData(self, data):
        
        #set parent data
        super(Supplier, self).setData(data)
        
        #set supplier data
        if "discount" in data: self.discount = data["discount"]
        if "terms" in data: self.terms = data['terms']
        
        #save self
        self.save()
        
        #set the address
        
        if "addressID" in data:
            address = Address.objects.get(id=data['addressID'])
        else:
            address = Address()
            
        if "address1" in data: address.address1 = data["address1"]
        if "address2" in data: address.address2 = data["address2"]
        if "city" in data: address.city = data["city"]
        if "territory" in data: address.territory = data["territory"]
        if "country" in data: address.country = data["country"]
        if "zipcode" in data: address.zipcode = data["zipcode"]
        if "terms" in data: self.term = data["terms"]
        
        #set the supplier to the address
        address.contact = self
        
        #save the address
        address.save()