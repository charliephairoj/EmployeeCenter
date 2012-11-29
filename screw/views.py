# Create your views here.

from screw.models import Screw
from django.contrib.auth.decorators import login_required
from utilities.http import httpGETProcessor, httpPOSTProcessor, httpPUTProcessor, httpDELETEProcessor


@login_required
#Handles request for Lumber
def screw(request, screw_id='0'):
    
    if request.method == "GET":
        
        return httpGETProcessor(request, Screw, screw_id)
    
    elif request.method == "POST":
        
        
        return httpPOSTProcessor(request, Screw)
           
    elif request.method == "PUT":
        
        return httpPUTProcessor(request, Screw, screw_id)
    
    elif request.method == "DELETE":
        
        return httpDELETEProcessor(Screw, screw_id)
        
        
        