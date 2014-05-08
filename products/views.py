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

from products.models import Model, Configuration, Upholstery, Table, Rug
from utilities.http import process_api, save_upload
from auth.models import S3Object


@login_required
def model(request, model_id=0):
    return process_api(request, Model, model_id)


@login_required
def model_image(request):
    print 'ok'
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
