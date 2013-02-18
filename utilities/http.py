
from django.http import HttpResponse
import json

#primary function to process requests for supplies
#created in the REST format
def processRequest(request, classObject, ID=0):
    
    if request.method == "GET":
        return httpGETProcessor(request, classObject, ID)
    elif request.method == "POST":
        return httpPOSTProcessor(request, classObject)         
    elif request.method == "PUT":       
        return httpPUTProcessor(request, classObject, ID)
    elif request.method == "DELETE":      
        return httpDELETEProcessor(request, classObject, ID)
    
    
#processes standard get requests
def httpGETProcessor(request, Class, class_id):
   
    user = request.user
   
   
    #determine if to get a specific Item
    if class_id == 0 or class_id == '0':
        #create an array to hold data
        data = []
        #loop through all items
        for model in Class.objects.all():
            #add the data to the model
            data.append(model.get_data(user=user))
    #If specific Item requested
    else:
        
        #add data to object
        data = Class.objects.get(id=class_id).get_data(user=user)
        
    #create the response with serialized json data
    response = HttpResponse(json.dumps(data), mimetype="application/json")
    #apply status code
    response.status_code = 200
    #return the response
    return response


#Processes Post request
#which is to create an object

def httpPOSTProcessor(request, Class):
    
    
    #Create a new Class
    model = Class()
    #Get the raw data
    try:
        data = json.loads(request.body)
    except:
        data = json.loads(request.POST.get('data'))
    #convert the information to the model
    model.set_data(data, user=request.user)
    model.save()
   
    #creates a response from serialize json      
    response = HttpResponse(json.dumps(model.get_data(user=request.user)), mimetype="application/json")
    #adds status code
    response.status_code = 201
    #returns the response
    return response


#Processes PUT requests
#which is to update an object

def httpPUTProcessor(request, Class, class_id):
   
    # Create a Task
    model = Class.objects.get(id=class_id)
        
    #change to put
    request.method = "POST"
    request._load_post_and_files();
    # Load data
    data = json.loads(request.body)
    
    request.method = "PUT"
    #Assigns the data to the  model
    model.set_data(data, user=request.user)
    # attempt to save
    model.save()
    #create response from serialized json data
    response = HttpResponse(json.dumps(model.get_data(user=request.user)), mimetype="application/json")
    response.status_code = 201
    return response


#Processes the DELETE request
def httpDELETEProcessor(request, Class, class_id):
    #get the model
    model = Class.objects.get(id=class_id)
    #delete the model
    model.delete()
    #create a response with a success status
    response = HttpResponse(json.dumps({'status':'success'}), mimetype="application/json")
    #add a status code to the response
    response.status_code = 203
    #return the response
    return response





