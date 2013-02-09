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

    if request.method == "POST":
        data = json.loads(request.POST.get('data'))
        ack = Acknowledgement()
        url = ack.create(data, user=request.user)
        data = ack.get_data()
        data.update({'url':url})
        return HttpResponse(json.dumps(data), mimetype="application/json")
    
#Get url
def acknowledgement_url(request, ack_id=0):
    if ack_id != 0 and request.method == "GET":
        ack = Acknowledgement.object.get(id=ack_id)
        