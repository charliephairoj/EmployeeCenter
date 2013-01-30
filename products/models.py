from django.db import models
from boto.s3.connection import S3Connection, Location
from boto.s3.key import Key
from django.conf import settings
import logging

logger = logging.getLogger('EmployeeCenter');
# Create your models here.

#Primary Product class
#where all the other product 
#types will inherit from including
# upholstery, tables, cabinets

class Product(models.Model):
    type = models.CharField(max_length=100)
    wholesale_price = models.DecimalField(null=True, max_digits=15, decimal_places=2, db_column='wholesale_price')
    manufacture_price = models.DecimalField(null=True, max_digits=15, decimal_places=2, db_column='manufacture_price')
    retail_price = models.DecimalField(null=True, max_digits=15, decimal_places=2, db_column='retail_price')
    width = models.IntegerField(db_column='width', default=0)
    depth = models.IntegerField(db_column='depth', default=0)
    height = models.IntegerField(db_column='height', default=0)
    units = models.CharField(max_length=20, default='mm')
    internalUnits = 'mm',
    externalUnits = 'mm',
    
   
    
#Upholstery section

#Creates the Models
class Model(models.Model):
    model = models.CharField(max_length=100, null=True)
    name = models.CharField(max_length=100, null=True)
    collection = models.CharField(max_length=100, null=True)
    isActive = models.BooleanField(default=True, db_column='is_active')
    dateCreated = models.DateField(auto_now=True, auto_now_add=True, null=True, db_column='date_created')
    
    #Methods
    def __unicode__(self):
        return self.model
    #Get Data as object
    def getData(self):
        #prepares array for configs
        configs = [];
        #loop through the products to get config
        for product in self.upholstery_set.all():
            configs.append({'configuration':product.configuration.configuration, 'configID':product.configuration.id})
        #Prepares array to hold image
        images = []
        #iterates over images and adds url to array
        for image in self.modelimage_set.all():
            images.append(image.url)
        #Sets the data object
        data = {
               "id":self.id, 
               "model":self.model,
               "name":self.name, 
               "collection":self.collection,
               #"year":model.dateCreated.year,
               "images":images, 
               "configurations":configs
        }
        #returns the data object
        return data
    
    def setData(self, data):
        if "model" in data: self.model = data["model"]
        if "name" in data: self.name = data["name"]
        if "collection" in data: self.collection = data["collection"]
    
class ModelImage(models.Model):
    model = models.ForeignKey(Model)
    url = models.TextField();
    bucket = models.TextField();
    key = models.TextField();
    
    #Methods
    
    #This method uploads the file to s3
    def uploadImage(self, image):
        
        if image.content_type == "image/jpeg":
            #Get Filename and set extension
            extension = 'jpg'
            
            #Save self to get id
            self.save()
            #start connection
            conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
            #get the bucket
            bucket = conn.get_bucket('media.dellarobbiathailand.com', True)
            #Create a key and assign it 
            k = Key(bucket)
            
            #Set file name
            k.key = 'model_images/'+str(self.id)+'.'+extension
            #upload file
            k.set_contents_from_file(image)
            #set the Acl
            k.set_acl('public-read')
            #set Url, key and bucket
            self.url = "http://media.dellarobbiathailand.com.s3.amazonaws.com/"+k.key
            self.key = k.key
            self.bucket = 'media.dellarobbiathailand.com'
            self.save()
           
#Creates the Configurations
class Configuration(models.Model):
    configuration = models.CharField(max_length=200)
    
    #Methods
    def __unicode__(self):
        return self.configuration
    
    #Sets the data
    def setData(self, data):
        if "configurationID" in data: self.id = data["configurationID"]
        if "configuration" in data: self.configuration = data["configuration"]
    
    #Gets the data as an object
    def getData(self):
        raw = {
            "id":self.id,
            "configuration":self.configuration
        }
        return raw
    
#Creates the Upholster class
#that inherits from Products
class Upholstery(Product):
    model = models.ForeignKey(Model, on_delete=models.PROTECT)
    configuration = models.ForeignKey(Configuration, on_delete=models.PROTECT)
    category = models.CharField(max_length=50)
    
    #Methods
    
    #Get Data as object
    def getData(self):
        raw = {
            "id":self.id,
            "type":"upholstery",
            'manufacture_price':str(self.manufacture_price),
            'wholesale_price':str(self.wholesale_price),
            'retail_price':str(self.retail_price),
            "model":{
                     "id":self.model.id,
                     "model":self.model.model,
                     "name":self.model.name
            },
            "configuration":{
                             "id ":self.configuration.id,
                             "configuration":self.configuration.configuration
            }
        }
         
        return raw
    
    #Set the data
    def setData(self, data):
        #Searches for the corresponing Model
        #and applies it to the upholster
        if "modelID" in data:
            model = Model.objects.get(id=data["modelID"])
            self.model = model
        #Searches for the corresponding Cofniguration
        #and applies it to the uploster
        if "configurationID" in data: 
            config = Configuration.objects.get(id=data["configurationID"])
            self.configuration = config
        if "retailPrice" in data: self.retailPrice = data["retailPrice"]
        if "wholesalePrice" in data: self.wholesalePrice = data["wholesale"]
        #Set the dimension
        if "width" in data: self.width = data["width"]
        if "depth" in data: self.depth = data["depth"]
        if "height" in data: self.height = data["height"]

#Creates the pillows for the upholstery
class UpholsteryPillows(models.Model):
    upholstery = models.ForeignKey(Upholstery)
    type = models.CharField(max_length=50)
    
#Creates the Table class
#that inherits from Products
class Tables(Product):
    model = models.ForeignKey(Model, on_delete=models.PROTECT)
