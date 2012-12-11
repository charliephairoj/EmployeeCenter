# Create your views here.

from zipper.models import Zipper
from django.contrib.auth.decorators import login_required
from utilities.http import httpGETProcessor, httpPOSTProcessor, httpPUTProcessor, httpDELETEProcessor


@login_required
#Handles request for Zipper
def zipper(request, zipper_id='0'):
    
    if request.method == "GET":
        
        return httpGETProcessor(request, Zipper, zipper_id)
    
    elif request.method == "POST":
        
        
        return httpPOSTProcessor(request, Zipper)
           
    elif request.method == "PUT":
        
        return httpPUTProcessor(request, Zipper, zipper_id)
    
    elif request.method == "DELETE":
        
        return httpDELETEProcessor(Zipper, zipper_id)
        
        
        