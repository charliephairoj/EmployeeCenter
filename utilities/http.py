
from django.http import HttpResponse
import json


#processes standard get requests
def httpGETProcessor(request, Model, ID):
    #determine if to get a specific Item
    if ID == 0 or ID == '0':
        #create an array to hold data
        data = []
        #loop through all items
        for model in Model.objects.all():
            #add the data to the model
            data.append(model.getData())
    #If specific Item requested
    else:
        #add data to object
        data = Model.objects.get(id=ID).getData()
        
    #create the response with serialized json data
    response = HttpResponse(json.dumps(data), mimetype="application/json")
    #apply status code
    response.status_code = 200
    #return the response
    return response


#Processes Post request
#which is to create an object

def httpPOSTProcessor(request, Model):
    
    
    #Create a new Model
    model = Model()
    #Get the raw data
    data = json.loads(request.POST.get('data'))
    #convert the information to the model
    model.setData(data)
    model.save()
   
            
    #creates a response from serialize json      
    response = HttpResponse(json.dumps(model.getData()), mimetype="application/json")
    #adds status code
    response.status_code = 201
    #returns the response
    return response


#Processes PUT requests
#which is to update an object

def httpPUTProcessor(request, Model, ID):
    
    # Create a Task
    model = Model.objects.get(id=ID)
        
    #change to put
    request.method = "POST"
    request._load_post_and_files();
    # Load data
    data = json.loads(request.POST.get('data'))
    #Assigns the data to the  model
    model.setData(data)
    # attempt to save
    model.save()
    #create response from serialized json data
    response = HttpResponse(json.dumps(model.getData()), mimetype="application/json")
    response.status_code = 201
    return response


#Processes the DELETE request
def httpDELETEProcessor(Model, ID):
    #get the model
    model = Model.objects.get(id=ID)
    #delete the model
    model.delete()
    #create a response with a success status
    response = HttpResponse(json.dumps({'status':'success'}), mimetype="application/json")
    #add a status code to the response
    response.status_code = 203
    #return the response
    return response





