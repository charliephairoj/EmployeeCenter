from wool.models import Wool
import json
from django.http import HttpResponseRedirect, HttpResponse
from utilities.http import httpGETProcessor, httpPOSTProcessor, httpPUTProcessor, httpDELETEProcessor






#Handles request for Lumber
def wool(request, wool_id='0'):
    if request.method == "GET":
        
        return httpGETProcessor(request, Wool, wool_id)
        
    elif request.method == "POST":
        
        return httpPOSTProcessor(request, Wool)
    
    elif request.method == "PUT":
        
        return httpPUTProcessor(request, Wool, wool_id)
    
    elif request.method == "DELETE":
        
        return httpDELETEProcessor(Wool, wool_id)
    
    
    
    
    