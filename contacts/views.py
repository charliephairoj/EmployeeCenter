
import json

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from contacts.models import Supplier, SupplierContact, Customer, Contact
from utilities.http import httpPOSTProcessor, httpGETProcessor, httpPUTProcessor, httpDELETEProcessor, processRequest


#Customer View
@login_required
def contact(request, contact_id=0):
    return processRequest(request, Contact, contact_id)


@login_required
def customer(request, customer_id=0):
    return processRequest(request, Customer, customer_id)

#Create the contacts view
@login_required
def supplier(request, supplier_id='0'):
    return processRequest(request, Supplier, supplier_id)

#Supplier contact View   
@login_required 
def supplierContact(request, supplier_contact_id=0):
    return processRequest(request, SupplierContact, supplier_contact_id)
    