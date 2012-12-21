from contacts.models import Supplier
from utilities.http import httpPOSTProcessor, httpGETProcessor, httpPUTProcessor, httpDELETEProcessor, processRequest
from django.http import HttpResponse
import json

#Create the contacts view
def supplier(request, supplier_id='0'):
    
    return processRequest(request, Supplier, supplier_id)
    
def supplierContact(request, supplier_contact_id=0):
    
    from contacts.models import SupplierContact
    
    if request.method == "GET":
        
        return httpGETProcessor(request, SupplierContact, supplier_contact_id)
    
    elif request.method == "DELETE":
        
        return httpDELETEProcessor(request, SupplierContact, supplier_contact_id)