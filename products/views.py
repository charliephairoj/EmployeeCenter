# Create your views here.

import os
import logging
import time
import json

from boto.s3.connection import S3Connection
from boto.s3.key import Key
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from products.models import Model, Configuration, Upholstery, Table
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


def process_api(request, cls, id):
    """
    The API interface for the upholstery model.
    """
    if request.method == "GET":
        if id == 0:
            data = [obj.to_dict(request.user) for obj in cls.objects.all()]
            return HttpResponse(json.dumps(data), mimetype='application/json')
        else:
            try:
                obj = cls.objects.get(id=id)
                return HttpResponse(json.dumps(obj.to_dict(request.user)), mimetype='application/json')
            except:
                return HttpResponseNotFound()

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
        except:
            return HttpResponseBadRequest("No data sent")

        if id == 0:
            try:
                obj = cls.create(user=request.user, **data)
            except AttributeError as e:
                return HttpResponseBadRequest(e.message)
            return HttpResponse(json.dumps(obj.to_dict(user=request.user), mimetype="application/json", status=201))
        else:
            obj = get_object_or_404(Upholstery, pk=id)
            try:
                obj.update(**data)
            except AttributeError as e:
                return HttpResponseBadRequest(e.message)
            return HttpResponse(json.dumps(obj.to_dict(user=request.user), mimetype="application/json", status=201))

    elif request.method == "DELETE":
            obj = get_object_or_404(cls, pk=id)
            obj.delete()
            return HttpResponse("Upholstery deleted.", status=200)


@login_required
def model(request, model_id=0):
    return process_api(request, Model, model_id)


@login_required
def model_image(request):
    if request.method == "POST":
        filename = save_upload(request)
        data = upload_image(filename, "products/model/{0}.jpg".format(time.time()))
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 201
        return response

@login_required
def configuration(request, configuration_id=0):
    return process_api(request, Configuration, configuration_id)


@login_required
def upholstery(request, uphol_id=0):
    return process_api(request, Upholstery, uphol_id)


@login_required
def table(request, table_id=0):
    return process_api(request, Table, table_id)


@login_required
def upholstery_image(request):
    if request.method == "POST":
        filename = save_upload(request)
        data = upload_image(filename, "products/upholstery/{0}.jpg".format(time.time()))
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 201
        return response
