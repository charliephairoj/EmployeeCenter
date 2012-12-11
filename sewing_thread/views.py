# Create your views here.

from sewing_thread.models import SewingThread
from django.contrib.auth.decorators import login_required
from utilities.http import httpGETProcessor, httpPOSTProcessor, httpPUTProcessor, httpDELETEProcessor


@login_required
#Handles request for SewingThread
def sewing_thread(request, sewing_thread_id='0'):
    
    if request.method == "GET":
        
        return httpGETProcessor(request, SewingThread, sewing_thread_id)
    
    elif request.method == "POST":
        
        
        return httpPOSTProcessor(request, SewingThread)
           
    elif request.method == "PUT":
        
        return httpPUTProcessor(request, SewingThread, sewing_thread_id)
    
    elif request.method == "DELETE":
        
        return httpDELETEProcessor(SewingThread, sewing_thread_id)
        
        
        