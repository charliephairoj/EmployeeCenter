from contacts.models import Supplier
from utilities.http import httpPOSTProcessor, httpGETProcessor, httpPUTProcessor, httpDELETEProcessor
from django.http import HttpResponse
import json

#Create the contacts view
def supplier(request, supplier_id='0'):
    
    
    
    if request.method == "GET":
        
        return httpGETProcessor(request, Supplier, supplier_id)
        
    elif request.method == "POST":
        
        return httpPOSTProcessor(request, Supplier)
    
    elif request.method == "PUT":
        
        return httpPUTProcessor(request, Supplier, supplier_id)
    
    elif request.method == "DELETE":
        
        return httpDELETEProcessor(request, Supplier, supplier_id)