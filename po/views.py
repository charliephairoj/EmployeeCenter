# Create your views here.

#import
from po.models import PurchaseOrder
from django.http import HttpResponseRedirect, HttpResponse
import json





#functions
def purchaseOrder(request, poID=0):
    
    #if post method
    if request.method == "POST":
        #create instance of po
        po = PurchaseOrder()
        #get the data
        data = json.loads(request.POST.get('data'))
        #create po
        po.create(data)
        #create the response and send 
        response = HttpResponse(json.dumps(po.getData()), mimetype="application/json")
        response.status_code = 201
        return response
        
        