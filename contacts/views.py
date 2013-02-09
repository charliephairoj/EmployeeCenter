
import json
from django.http import HttpResponse
from contacts.models import Supplier, SupplierContact, Customer
from utilities.http import httpPOSTProcessor, httpGETProcessor, httpPUTProcessor, httpDELETEProcessor, processRequest

#Customer View
def customer(request, customer_id=0):
    return processRequest(request, Customer, customer_id)

#Create the contacts view
def supplier(request, supplier_id='0'):
    return processRequest(request, Supplier, supplier_id)

#Supplier contact View    
def supplierContact(request, supplier_contact_id=0):
    return processRequest(request, SupplierContact, supplier_contact_id)
    