# Create your views here.

#import
from po.models import PurchaseOrder
from django.http import HttpResponseRedirect, HttpResponse
import json





#functions
def purchase_order(request, po_id=0):
    
    #if post method
    if request.method == "POST":
        #create instance of po
        po = PurchaseOrder()
        #get the data
        data = json.loads(request.POST.get('data'))
        #create po
        po.create(data)
        #create the response and send 
        response = HttpResponse(json.dumps(po.get_data()), mimetype="application/json")
        response.status_code = 201
        return response
        
        