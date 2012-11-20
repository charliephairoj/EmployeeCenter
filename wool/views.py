from wool.models import Wool
import json
from django.http import HttpResponseRedirect, HttpResponse
import logging

logger = logging.getLogger('EmployeeCenter');

from django.contrib.staticfiles.views import serve

def display(request):
    return serve(request, 's3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/DRLogo.jpg')





#Handles request for Lumber
def wool(request, woolID='0'):
    if request.method == "GET":
        #Create the array
        data = []
        #Loop to access all models
        for wool in Wool.objects.all():
            
            #Add raw data to array
            data.append(wool.getData()) 
            
           
            
        return HttpResponse(json.dumps(data), mimetype="application/json")
        
    elif request.method == "POST":
        
        if woolID == '0':
            logger.debug(request.POST);
            #Create a new Model
            wool = Wool()
            #Get the raw data
            postData = json.loads(request.POST.get('data'))
            #convert the information to the model
            wool.setData(postData)
            wool.save()
            #Gets the images and assigns them
            
            
            
            #response = HttpResponse(json.dumps({'lumberID':lumberID, 'filedata':request.FILES, 'modelData':newModel}), mimetype="application/json")
            response = HttpResponse(json.dumps(wool.getData()), mimetype="application/json")
            response.status_code = 201
            return response
        
        else:
            # Create a Task
            wool = Wool.objects.get(id=woolID)
            # Load data
            rawData = json.loads(request.POST.get('data'))
            #Assigns the data to the  model
            wool.setData(rawData)
            # attempt to save
            #model.save()
            # return just the plain hash
            # returning Location header causes problems
            response = HttpResponse(json.dumps(wool.getData()), mimetype="application/json")
            response.status_code = 201
            return response
    elif request.method == "DELETE":
        logger.debug(woolID)
        wool = Wool.objects.get(id=woolID)
        wool.delete()
        response = HttpResponse(json.dumps({'delete':'success'}), mimetype="application/json")
        response.status_code = 203
        return response