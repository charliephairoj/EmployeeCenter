# Create your views here.

from staple.models import Staple
from django.contrib.auth.decorators import login_required
from utilities.http import httpGETProcessor, httpPOSTProcessor, httpPUTProcessor, httpDELETEProcessor


@login_required
#Handles request for Staple
def staple(request, staple_id='0'):
    
    if request.method == "GET":
        
        return httpGETProcessor(request, Staple, staple_id)
    
    elif request.method == "POST":
        
        
        return httpPOSTProcessor(request, Staple)
           
    elif request.method == "PUT":
        
        return httpPUTProcessor(request, Staple, staple_id)
    
    elif request.method == "DELETE":
        
        return httpDELETEProcessor(Staple, staple_id)
        
        
        