from supplies.models import Supply
import json
from django.http import HttpResponseRedirect, HttpResponse
import logging

logger = logging.getLogger('EmployeeCenter');


def processRequest(request, classObject, ID='0'):
    #Action for a get request
    if request.method == "GET":
        #determines if request for
        #specific item
        if ID == '0':
            #create array 
            data = []
            #iterate through array
            for supply in classObject.objects.all():
                
                #add data to array
                data.append(supply.getData())
        #gets a specific item       
        else:
            #set data to item
            data = classObject.objects.get(id=ID)
        
        #return response    
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 200
        return response
#Handles projects
def supply(request, supplyID='0'):
    logger.debug('oop')
    return processRequest(request, Supply, supplyID)
    
    



