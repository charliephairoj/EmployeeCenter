from contacts.models import Supplier
from django.http import HttpResponse
import json
import logging

logger = logging.getLogger('EmployeeCenter');
#Create the contacts view
def supplier(request, supplierID='0'):
    
    if request.method == "GET":
        
        #check if id is 0
        #this determine whether
        #to get a specific contact or
        #all contacts
        if supplierID == '0':
            #set up array to hold contacts
            data = []
            #loop through all contacts
            for supplier in Supplier.objects.all():
                #Adds data to the array
                data.append(supplier.getData())
            
        
        else:
            #get the data from specified contact
            data =  Supplier.objects.get(id = supplierID).getData()
        
        return HttpResponse(json.dumps(data), mimetype="application/json")
        
    elif request.method == "POST":
        #creates a new contact
        if supplierID == '0':
            newSupplier = Supplier()
        else:
            newSupplier = Supplier.objects.get(id = supplierID)
        #get the data
        data = json.loads(request.POST.get('data'))
        #set the data
        newSupplier.setData(data)

        return HttpResponse(json.dumps(newSupplier.getData()), mimetype="application/json")
    
    elif request.method == "PUT":
        #creates a new contact
        
        supplier = Supplier.objects.get(id = supplierID)
        #RELOAD PUT DATA
        request.method = "POST"
        request._load_post_and_files();
        #get the data
        data = json.loads(request.POST.get('data'))
        #set the data
        supplier.setData(data)

        return HttpResponse(json.dumps(supplier.getData()), mimetype="application/json")
    
    elif request.method == "DELETE":
        logger.debug(supplierID)
        supplier = Supplier.objects.get(id = supplierID)
        
        supplier.delete()
        
    
    
        return HttpResponse(json.dumps({'yay':'ok'}), mimetype="application/json")
    
    
    
    