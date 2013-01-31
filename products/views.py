# Create your views here.

from products.models import Model, Configuration, Upholstery
from utilities.http import processRequest
from django.http import HttpResponse
import logging
import time
import json


#Create the Models Views

#Handles forming model guid



#Handles request for Models
def model(request, model_id=0):
    
    return processRequest(request, Model, model_id)


#Handles request for configs
def configuration(request, configuration_id=0):
    
    return processRequest(request, Configuration, configuration_id)
       


#Handles request for u
def upholstery(request, uphol_id=0):
    
    return processRequest(request, Upholstery, uphol_id)
        
        
        
def upholstery_image(request):
    
    if request.method == "POST":
        
        from django.conf import settings
        from boto.s3.connection import S3Connection
        from boto.s3.key import Key
        import os
        
        image = request.FILES['image']
        filename = settings.MEDIA_ROOT+str(time.time())+'.jpg'
           
        with open(filename, 'wb+' ) as destination:
            for chunk in image.chunks():
                destination.write(chunk)
        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        #get the bucket
        bucket = conn.get_bucket('media.dellarobbiathailand.com', True)
        #Create a key and assign it 
        k = Key(bucket)
                
        #Set file name
        k.key = "products/upholstery/%f.jpg" % (time.time())
        #upload file
            
        k.set_contents_from_filename(filename)
            
        #remove file from the system
        os.remove(filename)
        #set the Acl
        k.set_canned_acl('public-read')
        k.make_public()
         
        #set Url, key and bucket
        data = {
                'url':'http://media.dellarobbiathailand.com.s3.amazonaws.com/'+k.key,
                'key':k.key,
                'bucket':'media.dellarobbiathailand.com'
        }
            
        #self.save()
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 201
        return response
        