# Create your views here.

import json

from django.http import HttpResponse
from utilities.http import process_api

from po.models import PurchaseOrder


#functions
def purchase_order(request, po_id=0):

    #if post method
    if request.method == "POST" and po_id == 0:
        #get the data
        data = json.loads(request.body)
        #create po
        po = PurchaseOrder.create(user=request.user, **data)
        #create the response and send
        response = HttpResponse(json.dumps(po.dict()), mimetype="application/json")
        print po.dict()
        response.status_code = 201
        return response

    elif request.method == "GET":
        return process_api(request, PurchaseOrder, po_id)