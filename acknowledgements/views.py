# Create your views here.
import json
import os
import time
import dateutil.parser

from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from acknowledgements.models import Acknowledgement, Item, Delivery
from auth.models import S3Object
from utilities.http import save_upload, process_api


@login_required
def acknowledgement(request, ack_id=0):
    #Get Request
    if request.method == "GET":
        if ack_id == 0:
            params = request.GET
            acks = Acknowledgement.objects.all().order_by('-id')

            if "start_date" in params and "end_date" in params:
                start_date = dateutil.parser.parse(params['start_date'])
                end_date = dateutil.parser.parse(params['end_date'])
                acks = acks.filter(delivery_date__range=[start_date, end_date])
            elif "start_date" in params:
                start_date = dateutil.parser.parse(params['start_date'])
                acks = acks.filter(delivery_date__gte=start_date)
            elif "end_date" in params:
                end_date = dateutil.parser.parse(params['end_date'])
                acks = acks.filter(delivery_date__lte=end_date)
            elif "date" in params:
                date = dateutil.parser.parse(params['date'])
                acks = acks.filter(delivery_date=date)
            if "last_modified" in params:
                timestamp = dateutil.parser.parse(params["last_modified"])
                acks = acks.filter(last_modified__gte=timestamp)

            data = [ack.to_dict() for ack in acks]
        else:
            ack = Acknowledgement.objects.get(id=ack_id)
            data = ack.to_dict()

        response = HttpResponse(json.dumps(data), mimetype="application/json")
        return response

    if request.method == "POST":
        if ack_id == 0:
            data = json.loads(request.body)

            #Create the acknowledgement
            try:
                acknowledgement = Acknowledgement.create(request.user, **data)
            except TypeError as e:
                print e
                message = "Error: {0}".format(e)
                print message
                response = HttpResponse(message, mimetype="plain/text")
                response.status_code = 501
                return response

            response_data = acknowledgement.to_dict()
            response_data["acknowledgement_url"] = acknowledgement.generate_url('acknowledgement')
            response_data["production_url"] = acknowledgement.generate_url('production')
            return HttpResponse(json.dumps(response_data), mimetype="application/json")

        else:
            data = json.loads(request.body)
            acknowledgement = Acknowledgement.objects.get(id=ack_id)
            acknowledgement.update(data, request.user)
            response_data = acknowledgement.to_dict()
            response_data["acknowledgement_url"] = acknowledgement.generate_url('acknowledgement')
            response_data["production_url"] = acknowledgement.generate_url('production')
            return HttpResponse(json.dumps(response_data), mimetype="application/json")


@login_required
def item(request, ack_item_id=0):
    #Get Request
    if request.method == "GET" and ack_item_id == 0:
        params = request.GET
        items = Item.objects.all()
        if "status" in params:
            if params["status"].lower() == 'inventory' :
                items = items.exclude(Q(status='SHIPPED'), Q(status='ACKNOWLEDGED'))
        if "last_modified" in params:
            timestamp = dateutil.parser.parse(params["last_modified"])
            items = items.filter(last_modified__gte=timestamp)

        response = HttpResponse(json.dumps([item.to_dict() for item in items]), mimetype="application/json")
        return response

    else:
        return process_api(request, Item, ack_item_id)


@login_required
def log(request, ack_id=0):
    if request.method == "GET":
        if ack_id != 0:
            try:
                data = [log.to_dict() for log in Acknowledgement.objects.get(id=ack_id).acknowledgementlog_set.all()]
            except Acknowledgement.DoesNotExist:
                raise Exception
            return HttpResponse(json.dumps(data), mimetype="application/json")


@login_required
def pdf(request, ack_id):
    if "type" in request.GET:
        acknowledgement = Acknowledgement.objects.get(id=ack_id)
        if request.GET["type"] == "acknowledgement":
            url = acknowledgement.generate_url('acknowledgement')
        elif request.GET["type"] == "production":
            url = acknowledgement.generate_url('production')
        data = {'url': url}
        return HttpResponse(json.dumps(data), mimetype="application/json")


@login_required
def acknowledgement_item_image(request):
    if request.method == "POST":
        filename = save_upload(request)
        obj = S3Object.create(filename,
                        "acknowledgement/item/image/{0}.jpg".format(time.time()),
                        'media.dellarobbiathailand.com')
        response = HttpResponse(json.dumps({'id': obj.id,
                                            'url': obj.generate_url()}),
                                content_type="application/json")
        response.status_code = 201
        return response


@login_required
def delivery(request):
    if request.method == "GET":
        data = [d.to_dict() for d in Delivery.objects.all()]
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 201
        return response
        
        
        
        
