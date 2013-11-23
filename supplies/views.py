import os
import json
import logging
import time

from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required

from supplies.models import Supply, SupplyLog
from utilities.http import process_api, save_upload
from auth.models import S3Object


logger = logging.getLogger('EmployeeCenter')


#Supplies
@login_required
def supply(request, supply_id=0):
    print request
    return process_api(request, Supply, supply_id)


#Reserve fabric
@login_required
def reserve(request, supply_id):
    POST_data = json.loads(request.body)
    quantity = POST_data["quantity"]
    try:
        ack_id = POST_data["remarks"]
    except:
        ack_id = None

    supply = Supply.objects.get(id=supply_id)
    supply.reserve(quantity, request.user, acknowledgement_id=ack_id)
    response = HttpResponse(json.dumps({'quantity': str(supply.quantity)}), mimetype="application/json")
    response.status_code = 200
    return response


#Add length to a fabric
@login_required
def add(request, supply_id):
    POST_data = json.loads(request.body)
    quantity = POST_data["quantity"]
    try:
        remarks = POST_data["remarks"]
    except:
        remarks = None
    supply = Supply.objects.get(id=supply_id)
    supply.add(quantity=quantity, employee=request.user, remarks=remarks)
    response = HttpResponse(json.dumps({'quantity': str(supply.quantity)}), mimetype="application/json")
    response.status_code = 200
    return response


#Subtracts length from a fabric
@login_required
def subtract(request, supply_id):
    POST_data = json.loads(request.body)
    quantity = POST_data["quantity"]
    try:
        ack_id = POST_data["remarks"]
    except:
        ack_id = None

    supply = Supply.objects.get(id=supply_id)
    supply.subtract(quantity, request.user, acknowledgement_id=ack_id)
    response = HttpResponse(json.dumps({'quantity': str(supply.quantity)}), mimetype="application/json")
    response.status_code = 200
    return response


#Resets Length from a fabric
@login_required
def reset(request, supply_id):
    POST_data = json.loads(request.body)
    quantity = POST_data["quantity"]
    try:
        remarks = POST_data["remarks"]
    except:
        remarks = None

    supply = Supply.objects.get(id=supply_id)
    supply.reset(quantity=quantity, employee=request.user, remarks=remarks)
    response = HttpResponse(json.dumps({'quantity': str(supply.quantity)}), mimetype="application/json")
    response.status_code = 200
    return response


#Fabric Log
@login_required
def supply_log(request, supply_id=0):
    if request.method == "GET":
        logs = SupplyLog.objects.filter(supply_id=supply_id).order_by('-timestamp')
        data = []
        for log in logs:
            data_item = {'acknowledgement_id': log.acknowledgement_id,
                         'event': log.event,
                         'quantity': str(log.quantity),
                         'remarks': log.remarks,
                         'employee': "%s %s" %(log.employee.first_name, log.employee.last_name),
                         'timestamp': log.timestamp.strftime('%B %d, %Y %H:%M:%S')}
            data.append(data_item)
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 200
        return response
    

#uploads a fabric
@login_required
def supply_image(request):
    if request.method == "POST":
        filename = save_upload(request)
        image = S3Object.create(filename,
                        "supply/image/{0}.jpg".format(time.time()),
                        "media.dellarobbiathailand.com")
        #set Url, key and bucket
        data = {'url': image.generate_url(),
                "id": image.id,
                'key': image.key,
                'bucket': image.bucket}
        #self.save()
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 201
        return response


#fabric
@login_required
def fabric(request, fabric_id=0):
    from supplies.models import Fabric
    return process_api(request, Fabric, fabric_id)


#foam
@login_required
def foam(request, foam_id=0):
    from supplies.models import Foam
    return process_api(request, Foam, foam_id)


@login_required
def glue(request, glue_id=0):
    from supplies.models import Glue
    return process_api(request, Glue, glue_id)


#lumber
@login_required
def lumber(request, lumber_id=0):
    from supplies.models import Lumber
    return process_api(request, Lumber, lumber_id)


@login_required
def sewing_thread(request, sewing_thread_id=0):
    from supplies.models import SewingThread
    return process_api(request, SewingThread, sewing_thread_id)


@login_required
def screw(request, screw_id=0):
    from supplies.models import Screw
    return process_api(request, Screw, screw_id)


@login_required
def staple(request, staple_id=0):
    from supplies.models import Staple
    return process_api(request, Staple, staple_id)


@login_required
def webbing(request, webbing_id=0):
    from supplies.models import Webbing
    return process_api(request, Webbing, webbing_id)


@login_required
def wool(request, wool_id=0):
    from supplies.models import Wool
    return process_api(request, Wool, wool_id)


@login_required
def zipper(request, zipper_id=0):
    from supplies.models import Zipper
    return process_api(request, Zipper, zipper_id)
