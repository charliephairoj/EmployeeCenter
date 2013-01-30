# Create your views here.
from django.http import HttpResponse
from acknowledgements.models import Acknowledgement
import json

def acknowledgement(request):
    
    #Get Request
    if request.method == "GET":
        data = []
        for ack in Acknowledgement.objects.all().order_by('-id'):
            
            data.append(ack.get_data())
        
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        return response