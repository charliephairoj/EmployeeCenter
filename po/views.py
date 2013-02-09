# Create your views here.

import json
from django.http import HttpResponse
from utilities.http import httpGETProcessor
from po.models import PurchaseOrder






#functions
def purchase_order(request, po_id=0):
    
    #if post method
    if request.method == "POST":
        #create instance of po
        po = PurchaseOrder()
        #get the data
        data = json.loads(request.POST.get('data'))
        #create po
        po.create(data, user=request.user)
        #create the response and send 
        response = HttpResponse(json.dumps(po.get_data()), mimetype="application/json")
        response.status_code = 201
        return response
        
    elif request.method == "GET":
        
        return httpGETProcessor(request, PurchaseOrder, po_id)