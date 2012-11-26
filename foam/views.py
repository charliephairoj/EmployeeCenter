# Create your views here.

from foam.models import Foam
from django.contrib.auth.decorators import login_required
from utilities.http import httpGETProcessor, httpPOSTProcessor, httpPUTProcessor, httpDELETEProcessor
import logging

logger = logging.getLogger('EmployeeCenter');

@login_required
#Handles request for Lumber
def foam(request, foamID=0):
    logger.debug(request)
    logger.debug(foamID)
    
    if request.method == "GET":
        
        return httpGETProcessor(request, Foam, foamID)
    
    elif request.method == "POST":
        
        
        return httpPOSTProcessor(request, Foam)
           
    elif request.method == "PUT":
        
        return httpPUTProcessor(request, Foam, foamID)
    
    elif request.method == "DELETE":
        
        return httpDELETEProcessor(Foam, foamID)
        
        
        