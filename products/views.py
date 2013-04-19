# Create your views here.

import os
import logging
import time
import json

from boto.s3.connection import S3Connection
from boto.s3.key import Key
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required

from products.models import Model, Configuration, Upholstery
from utilities.http import processRequest


def save_upload(request, filename=None):
    if filename is None:
        filename = "{0}{1}.jpg".format(settings.MEDIA_ROOT,time.time())
    #Save File to disk
    image = request.FILES['image']
    filename = settings.MEDIA_ROOT+str(time.time())+'.jpg' 
    with open(filename, 'wb+' ) as destination:
        for chunk in image.chunks():
            destination.write(chunk)
    return filename


def upload_image(image, key, bucket='media.dellarobbiathailand.com', acl='public-read'):
    conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
    bucket = conn.get_bucket(bucket, True)
    k = Key(bucket)
    k.key = key
    k.set_contents_from_filename(image)
    os.remove(image)
    k.set_canned_acl(acl)
    k.make_public()
    data = {'url':'http://media.dellarobbiathailand.com.s3.amazonaws.com/'+k.key,
            'key':k.key,
            'bucket':'media.dellarobbiathailand.com'}
    return data


#Handles request for Models
@login_required
def model(request, model_id=0):
    return processRequest(request, Model, model_id)


@login_required
def model_image(request):
    if request.method == "POST":
        filename = save_upload(request)
        data = upload_image(filename, "products/model/{0}.jpg".format(time.time()))
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 201
        return response
    
    
#Handles request for configs
@login_required
def configuration(request, configuration_id=0):
    return processRequest(request, Configuration, configuration_id)
       

#Handles request for u
@login_required
def upholstery(request, uphol_id=0):
    return processRequest(request, Upholstery, uphol_id)
        

@login_required
def upholstery_image(request):
    if request.method == "POST":
        filename = save_upload(request)
        data = upload_image(filename, "products/upholstery/{0}.jpg".format(time.time()))
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 201
        return response
        