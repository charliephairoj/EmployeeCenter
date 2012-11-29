# Create your views here.

from webbing.models import Webbing
from django.contrib.auth.decorators import login_required
from utilities.http import httpGETProcessor, httpPOSTProcessor, httpPUTProcessor, httpDELETEProcessor


@login_required
#Handles request for Lumber
def webbing(request, webbing_id='0'):
    
    if request.method == "GET":
        
        return httpGETProcessor(request, Webbing, webbing_id)
    
    elif request.method == "POST":
        
        
        return httpPOSTProcessor(request, Webbing)
           
    elif request.method == "PUT":
        
        return httpPUTProcessor(request, Webbing, webbing_id)
    
    elif request.method == "DELETE":
        
        return httpDELETEProcessor(Webbing, webbing_id)
        
        
        