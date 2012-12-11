# Create your views here.

from lumber.models import Lumber
from django.contrib.auth.decorators import login_required
from utilities.http import httpGETProcessor, httpPOSTProcessor, httpPUTProcessor, httpDELETEProcessor


@login_required
#Handles request for Lumber
def lumber(request, lumber_id='0'):
    
    if request.method == "GET":
        
        return httpGETProcessor(request, Lumber, lumber_id)
    
    elif request.method == "POST":
        
        
        return httpPOSTProcessor(request, Lumber)
           
    elif request.method == "PUT":
        
        return httpPUTProcessor(request, Lumber, lumber_id)
    
    elif request.method == "DELETE":
        
        return httpDELETEProcessor(Lumber, lumber_id)
        
        
        