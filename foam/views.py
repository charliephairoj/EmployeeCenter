# Create your views here.
from django.contrib.auth.decorators import login_required

from foam.models import Foam
from utilities.http import httpGETProcessor, httpPOSTProcessor, httpPUTProcessor, httpDELETEProcessor

@login_required
#Handles request for Lumber
def foam(request, foam_id=0):
    
    
    if request.method == "GET":
        
        return httpGETProcessor(request, Foam, foam_id)
    
    elif request.method == "POST":
        
        
        return httpPOSTProcessor(request, Foam)
           
    elif request.method == "PUT":
        
        return httpPUTProcessor(request, Foam, foam_id)
    
    elif request.method == "DELETE":
        
        return httpDELETEProcessor(Foam, foam_id)
        
        
        