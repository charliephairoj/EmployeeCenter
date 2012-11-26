# Create your views here.

from fabric.models import Fabric
from django.contrib.auth.decorators import login_required
from utilities.http import httpGETProcessor, httpPOSTProcessor, httpPUTProcessor, httpDELETEProcessor



@login_required
#Handles request for Lumber
def fabric(request, fabricID=0):
    if request.method == "GET":
        
        return httpGETProcessor(request, Fabric, fabricID)
    
    elif request.method == "POST":
        
        return httpPOSTProcessor(request, Fabric)
        
           
    elif request.method == "PUT":
        
        return httpPUTProcessor(request, Fabric, fabricID)
    
    elif request.method == "DELETE":
        
        return httpDELETEProcessor(request, Fabric, fabricID)
    
    
    
    