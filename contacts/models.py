from django.db import models

# Create your models here.

#Creates the Contact Class
class Contact(models.Model):
    name = models.CharField(max_length=200)
    telephone = models.TextField()
    fax = models.TextField()
    email = models.CharField(max_length=200, null=True)
    is_supplier = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=False)
    currency = models.CharField(max_length=10, null=True)
 
    def get_data(self, user=None):
        #Structure data
        data = {'id':self.id,
                'name':self.name,
                'email':self.email,
                'telephone':self.telephone,
                'fax':self.fax,
                'isSupplier':self.is_supplier,
                'isCustomer':self.is_customer,
                'addresses':[],
                'currency':self.currency}
        #loop through all addresses and retrieve data
        for address in self.address_set.all():
            data['addresses'].append(address.get_data())
        #returns the data
        return data
    
    def set_data(self, data, user=None):
        if "name" in data: self.name = data["name"]
        if "email" in data: self.email = data["email"]
        if "telephone" in data: self.telephone = data["telephone"]
        if "fax" in data: self.fax = data["fax"]
        if "term" in data: self.term = data["term"]
        if "currency" in data: self.currency = data["currency"]
        #save the contact
        self.save()
        #set address
        if "address" in data:
            print data["address"]["id"]
            try:
                address = Address.objects.get(id=data["address"]["id"])
            except:
                address = Address() 
            address.set_data(data["address"])
            address.contact = self
            address.save()
        #set addresses
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
    latitude = models.DecimalField(decimal_places=6, max_digits=9)
    longitude = models.DecimalField(decimal_places=6, max_digits=9)
    
    def get_data(self):
        #Structure data
        data = {'id':self.id,
                'address1':self.address1,
                'address2':self.address2,
                'city':self.city,
                'territory':self.territory,
                'country':self.country,
                'zipcode':self.zipcode,
                'lat':self.latitude,
                'lng':self.longitude}
        #Return Data
        return data

    def set_data(self, data):
        if "address1" in data: self.address1 = data["address1"]
        if "address2" in data: self.address2 = data["address2"]
        if "city" in data: self.city = data["city"]
        if "territory" in data: self.territory = data["territory"]
        if "country" in data: self.country = data["country"]
        if "zipcode" in data: self.country = data["zipcode"]
        if "lat" in data: self.latitude = data['lat']
        if "lng" in data: self.longitude = data['lng']
       
#Customer class
class Customer(Contact):
    
    def get_data(self, user=None):
        #Get parent data
        data = super(Customer, self).get_data(user=None)
        #Return data
        return data
    
    def set_data(self, data, user=None):
        #Set parent data
        super(Customer, self).set_data(data, user=None)
    
#supplier class
class Supplier(Contact):
    terms = models.IntegerField(default=0)
    discount = models.IntegerField(default=0)
        
    #get data
    def get_data(self, user=None): 
        #Structure data
        data = {'terms':self.terms,
                'discount':self.discount,
                'contacts':[]}
        
        #Update with Parent data
        data.update(super(Supplier, self).get_data(user=user))
        #Add address dict and remove
        # the addresses dic
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
        if "discount" in data: self.discount = data["discount"]
        if "terms" in data: self.terms = data['terms']
        #save self
        self.save()
        #Add supplier contacts
        if "contacts" in data:
            for contact_data in data["contacts"]:
                #Decide if to create a new contact
                #or if to retrieve an existsing one 
                #based on if id exists
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
        data = {'id':self.id,
                'firstName':self.first_name,
                'lastName':self.last_name,
                'email':self.email,
                'telephone':self.telephone}
        #Return data
        return data
    
    def set_data(self, data, user=None):
        #Set data
        if "firstName" in data: self.first_name = data["firstName"]
        if "lastName" in data: self.last_name = data["lastName"]
        if "email" in data: self.email = data["email"]
        if "telephone" in data: self.telephone = data["telephone"]
     
    
    
    
    
    