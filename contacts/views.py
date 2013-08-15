
import json

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from contacts.models import Supplier, SupplierContact, Customer, Contact
from utilities.http import process_api


@login_required
def contact(request, contact_id=0):
    return process_api(request, Contact, contact_id)


@login_required
def customer(request, customer_id=0):
    return process_api(request, Customer, customer_id)


@login_required
def supplier(request, supplier_id=0):
    return process_api(request, Supplier, supplier_id)


@login_required
def supplierContact(request, supplier_contact_id=0):
    return process_api(request, SupplierContact, supplier_contact_id)
    