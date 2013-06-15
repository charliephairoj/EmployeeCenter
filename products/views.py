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

from products.models import Model, Configuration, Upholstery, Table, Rug
from utilities.http import processRequest
from auth.models import S3Object


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


def process_api(request, cls, obj_id):
    """
    The API interface for the upholstery model.
    """
    print obj_id
    if request.method == "GET":
        if obj_id == 0:
            data = [obj.to_dict(request.user) for obj in cls.objects.all()]
            return HttpResponse(json.dumps(data), content_type='application/json')
        else:
            try:
                obj = cls.objects.get(id=obj_id)
            except:
                return HttpResponseNotFound()

            return HttpResponse(json.dumps(obj.to_dict(request.user)), content_type='application/json')

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
        except:
            return HttpResponseBadRequest("No data sent")

        if obj_id == 0:
            try:
                obj = cls.create(user=request.user, **data)
            except AttributeError as e:
                return HttpResponseBadRequest(e.message)
            return HttpResponse(json.dumps(obj.to_dict(user=request.user)), content_type="application/json", status=201)
        else:
            obj = get_object_or_404(Upholstery, pk=obj_id)
            try:
                obj.update(user=request.user, **data)
            except AttributeError as e:
                return HttpResponseBadRequest(e.message)
            return HttpResponse(json.dumps(obj.to_dict(user=request.user)), content_type="application/json", status=201)

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
        obj = S3Object.create(filename,
                        "products/model/{0}.jpg".format(time.time()),
                        'media.dellarobbiathailand.com')
        response = HttpResponse(json.dumps({'id': obj.id,
                                            'url': obj.generate_url()}),
                                content_type="application/json")
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
def rug(request, rug_id=0):
    return process_api(request, Rug, rug_id)


@login_required
def upholstery_image(request):
    if request.method == "POST":
        filename = save_upload(request)
        obj = S3Object.create(filename,
                        "products/upholstery/{0}.jpg".format(time.time()),
                        'media.dellarobbiathailand.com')
        response = HttpResponse(json.dumps({'id': obj.id,
                                            'url': obj.generate_url()}),
                                content_type="application/json")
        response.status_code = 201
        return response
