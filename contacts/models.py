from django.db import models

# Create your models here.

#Creates the Contact Class
class Contact(models.Model):
    name = models.CharField(max_length=200)
    telephone = models.IntegerField()
    fax = models.IntegerField()
    email = models.CharField(max_length=200, null=True)
    isSupplier = models.BooleanField(default=False)
    isCustomer = models.BooleanField(default=False)
    
    
    
    def get_data(self):
        
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
                    'zipcode':address.zipcode,
                    'lat': address.latitude,
                    'lng': address.longitude
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
    
    def set_data(self, data):
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
    latitude = models.DecimalField(decimal_places=6, max_digits=9)
    longitude = models.DecimalField(decimal_places=6, max_digits=9)
    
    
    
    def set_data(self, data):
        if "address1" in data: self.address1 = data["address1"]
        if "address2" in data: self.address2 = data["address2"]
        if "city" in data: self.city = data["city"]
        if "territory" in data: self.territory = data["territory"]
        if "country" in data: self.country = data["country"]
        if "zipcode" in data: self.country = data["zipcode"]
        if "lat" in data: self.latitude = data['lat']
        if "lng" in data: self.longitude = data['lng']
    
#supplier class
class Supplier(Contact):
    terms = models.IntegerField(default=0)
    discount = models.IntegerField(default=0)
    #methods
    
    #get data
    def get_data(self):
        
        
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
                'discount':self.discount,
                'lat': None,
                'lng': None
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
            data["lng"] = address.longitude
            data['lat'] = address.latitude
        
        data['contacts'] = []
        #get supplier contacts
        for supplierContact in self.suppliercontact_set.all():
            data['contacts'].append(supplierContact.get_data())
        #returns the data
        return data
    #set data
    def set_data(self, data):
        
        #set parent data
        super(Supplier, self).set_data(data)
        
        #set supplier data
        if "discount" in data: self.discount = data["discount"]
        if "terms" in data: self.terms = data['terms']
        
        #save self
        self.save()
        
        #Add supplier contacts
        if "contacts" in data:
            for contactData in data["contacts"]:
                #Decide if to create a new contact
                #or if to retrieve an existsing one 
                #based on if id exists
                if "id" in contactData:
                    contact = SupplierContact.objects.get(id=contactData['id'])
                else:
                    contact = SupplierContact()
                
                #sets the details
                contact.set_data(contactData)
                contact.supplier = self
                
                contact.save()
        
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
        if "lat" in data: address.latitude = data['lat']
        if "lng" in data: address.longitude = data['lng']
        if "terms" in data: self.term = data["terms"]
        
        #set the supplier to the address
        address.contact = self
        
        #save the address
        address.save()
        
        
        
class SupplierContact(models.Model):
    
    first_name = models.TextField()
    last_name = models.TextField()
    email = models.TextField()
    telephone = models.TextField()
    supplier = models.ForeignKey(Supplier)
    
    def get_data(self):
        
        data = {'id':self.id,
                'firstName':self.first_name,
                'lastName':self.last_name,
                'email':self.email,
                'telephone':self.telephone}
        
        return data
    
    def set_data(self, data):
        
        if "firstName" in data: self.first_name = data["firstName"]
        if "lastName" in data: self.last_name = data["lastName"]
        if "email" in data: self.email = data["email"]
        if "telephone" in data: self.telephone = data["telephone"]
    
    
    
    
    
    