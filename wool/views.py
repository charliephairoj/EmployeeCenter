from wool.models import Wool
import json
from django.http import HttpResponseRedirect, HttpResponse
from utilities.http import httpGETProcessor, httpPOSTProcessor, httpPUTProcessor, httpDELETEProcessor






#Handles request for Lumber
def wool(request, woolID='0'):
    if request.method == "GET":
        
        return httpGETProcessor(request, Wool, woolID)
        
    elif request.method == "POST":
        
        return httpPOSTProcessor(request, Wool)
    
    elif request.method == "PUT":
        
        return httpPUTProcessor(request, Wool, woolID)
    
    elif request.method == "DELETE":
        
        return httpDELETEProcessor(Wool, woolID)
    
    
    
    
    