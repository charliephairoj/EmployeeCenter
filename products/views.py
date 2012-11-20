# Create your views here.

from products.models import Model, Configuration, Upholstery, ModelImage
import json
from django.http import HttpResponseRedirect, HttpResponse
import logging

logger = logging.getLogger('EmployeeCenter');

#Create the Models Views

#Handles forming model guid



#Handles request for Models
def model(request, modelID='0'):
    if request.method == "GET":
        #Create the array
        rawModels = []
        #Loop to access all models
        for model in Model.objects.all():
            
            #Add raw data to array
            rawModels.append(model.getData()) 
            
           
            
        return HttpResponse(json.dumps(rawModels), mimetype="application/json")
        
    elif request.method == "POST":
        
        if modelID == '0':
            #Create a new Model
            newModel = Model()
            #Get the raw data
            postData = json.loads(request.POST.get('data'))
            #convert the information to the model
            newModel.setData(postData)
            newModel.save()
            #Gets the images and assigns them
            images = request.FILES
            
            
            for preimage in images.items():
                #Extract image from tuple
                image = preimage[1]
                #New Model image 
                modelImage = ModelImage()
                #link to model
                modelImage.model = newModel
                #upload image
                modelImage.uploadImage(image)
            #response = HttpResponse(json.dumps({'modelID':modelID, 'filedata':request.FILES, 'modelData':newModel}), mimetype="application/json")
            response = HttpResponse(json.dumps({'model':newModel.getData()}), mimetype="application/json")
            response.status_code = 203
            return response
        
        else:
            # Create a Task
            model = Model.objects.get(id=modelID)
            # Load data
            rawData = json.loads(request.raw_post_data)
            #Assigns the data to the  model
            model.setData(rawData)
            # attempt to save
            #model.save()
            # return just the plain hash
            # returning Location header causes problems
            response = HttpResponse(json.dumps({'modelID':modelID, 'data':rawData}), mimetype="application/json")
            response.status_code = 212
            return response
    elif request.method == "DELETE":
        logger.debug(modelID)
        model = Model.objects.get(id=modelID)
        logger.debug(model)
        model.delete()
        response = HttpResponse(json.dumps({'delete':'success'}), mimetype="application/json")
        response.status_code = 203
        return response


#Handles request for configs
def configuration(request, configID = '0'):
    if request.method == "GET":
        #Create the array
        rawConfigs = []
        #Loop to access all models
        for config in Configuration.objects.all():
            
            #Add to array
            rawConfigs.append(config.getData())
            
           
       
        return HttpResponse(json.dumps(rawConfigs), mimetype="application/json")
        
    elif request.method == "POST":
        #check if update or create
        if configID == '0':
            # Create a Task
            config = Configuration()
            # Load data
            rawData = json.loads(request.raw_post_data)
            #Assigns the data to the  model
            config.setData(rawData)
            # attempt to save
            config.save()
            # return just the plain hash
            # returning Location header causes problems
            response = HttpResponse(json.dumps({"configuration": config.getData()}))
            response.status_code = 201
            return response
        else:
            config = Configuration.objects.get(id = configID)
            # Load data
            rawData = json.loads(request.raw_post_data)
            config.setData(rawData)
            response = HttpResponse(json.dumps({"configuration": config.getData()}))
            response.status_code = 201
            return response
    


       


#Handles request for u
def upholstery(request, upholID='0'):
    if request.method == "GET":
        #Create the array
        rawData = []
        #Loop to access all models
        for uphol in Upholstery.objects.all():
            
            #Add to array
            rawData.append(uphol.getData())
            
            
            
        return HttpResponse(json.dumps(rawData), mimetype="application/json")
        
    elif request.method == "POST":
        if upholID == '0':
            # Create a Task
            upol = Upholstery()
            # Load data
            rawData = json.loads(request.raw_post_data)
            #Assigns the data to the  model
            uphol.setData(rawData)
            # attempt to save
            upol.save()
            # return just the plain hash
            # returning Location header causes problems
            response = HttpResponse(json.dumps({"content": uphol.getData()}))
            response.status_code = 201
            return response
        