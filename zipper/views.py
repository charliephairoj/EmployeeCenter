# Create your views here.

from lumber.models import Lumber
from django.contrib.auth.decorators import login_required
from utilities.http import httpGETProcessor, httpPOSTProcessor, httpPUTProcessor, httpDELETEProcessor


@login_required
#Handles request for Lumber
def lumber(request, lumberID='0'):
    
    if request.method == "GET":
        
        return httpGETProcessor(request, Lumber, lumberID)
    
    elif request.method == "POST":
        
        
        return httpPOSTProcessor(request, Lumber)
           
    elif request.method == "PUT":
        
        return httpPUTProcessor(request, Lumber, lumberID)
    
    elif request.method == "DELETE":
        
        return httpDELETEProcessor(Lumber, lumberID)
        
        
        