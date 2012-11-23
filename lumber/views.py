# Create your views here.

from lumber.models import Lumber
import json
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
import logging

logger = logging.getLogger('EmployeeCenter');


@login_required
#Handles request for Lumber
def lumber(request, lumberID='0'):
    if request.method == "GET":
        
        if lumberID == '0':
            
            #Create the array
            data = []
            #Loop to access all models
            for lumber in Lumber.objects.all():
                
                #Add raw data to array
                data.append(lumber.getData()) 
        
        else:
            
            data = Lumber.objects.get(id=lumberID).getData()
            
           
            
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 200
        return response
    
    elif request.method == "POST":
        
        #Create a new Model
        lumber = Lumber()
        #Get the raw data
        postData = json.loads(request.POST.get('data'))
        #convert the information to the model
        lumber.setData(postData)
        lumber.save()
        #Gets the images and assigns them
            
            
            
        #response = HttpResponse(json.dumps({'lumberID':lumberID, 'filedata':request.FILES, 'modelData':newModel}), mimetype="application/json")
        response = HttpResponse(json.dumps(lumber.getData()), mimetype="application/json")
        response.status_code = 201
        return response
        
           
    elif request.method == "PUT":
        
        # Create a Task
        lumber = Lumber.objects.get(id=lumberID)
        
        #change to put
        request.method = "POST"
        request._load_post_and_files();
        # Load data
        rawData = json.loads(request.POST.get('data'))
        logger.debug(rawData)
        #Assigns the data to the  model
        lumber.setData(rawData)
        logger.debug(lumber.width)
        # attempt to save
        #model.save()
        # return just the plain hash
        # returning Location header causes problems
        response = HttpResponse(json.dumps(lumber.getData()), mimetype="application/json")
        response.status_code = 201
        return response
    
    elif request.method == "DELETE":
        lumber = Lumber.objects.get(id=lumberID)
        lumber.delete()
        response = HttpResponse(json.dumps({'delete':'success'}), mimetype="application/json")
        response.status_code = 203
        return response