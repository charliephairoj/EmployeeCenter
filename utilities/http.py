"""Utilities to help process views/REST Calls"""
import json
from dateutil import parser
import time

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils.datastructures import MultiValueDictKeyError
from django.core.paginator import Paginator


#primary function to process requests for supplies
#created in the REST format
def processRequest(request, classObject, ID=0):
    if request.method == "GET":
        return httpGETProcessor(request, classObject, ID)
    elif request.method == "POST":
        return httpPOSTProcessor(request, classObject, ID)
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
        GET_data = request.GET
        data = []
        objs = Class.objects.all()
        if "last_modified" in GET_data:
            try:
                timestamp = parser.parse(GET_data["last_modified"])
                objs = objs.filter(last_modified__gte=timestamp)
            except:
                pass
        #loop through all items
        for model in objs:
            #add the data to the model
            data.append(model.to_dict(user=user))
    #If specific Item requested
    else:

        #add data to object
        data = Class.objects.get(id=class_id).to_dict(user=user)

    #create the response with serialized json data
    response = HttpResponse(json.dumps(data), mimetype="application/json")
    #apply status code
    response.status_code = 200
    #return the response
    return response


#Processes Post request
#which is to create an object

def httpPOSTProcessor(request, Class, class_id=0):

    #Checks if a put processor should be used instead
    if class_id == 0 or class_id == '0':
        #Get the raw data
        try:
            data = json.loads(request.body)
        except:
            data = json.loads(request.POST.get('data'))
        #convert the information to the model
        model = Class.create(user=request.user, **data)

        #creates a response from serialize json
        response = HttpResponse(json.dumps(model.to_dict(user=request.user)),
                                mimetype="application/json")
        #adds status code
        response.status_code = 201
        #returns the response
        return response
    else:
        return httpPUTProcessor(request, Class, class_id)


#Processes PUT requests
#which is to update an object

def httpPUTProcessor(request, Class, class_id):
    # Create a Task
    model = Class.objects.get(id=class_id)
    #change to put
    request.method = "POST"
    request._load_post_and_files()
    # Load data
    data = json.loads(request.body)
    request.method = "PUT"
    #Assigns the data to the  model
    model.update(user=request.user, **data)
    # attempt to save
    model.save()
    #create response from serialized json data
    response = HttpResponse(json.dumps(model.to_dict(user=request.user)),
                            mimetype="application/json")
    response.status_code = 201
    return response


#Processes the DELETE request
def httpDELETEProcessor(request, Class, class_id):
    #get the model
    model = Class.objects.get(id=class_id)
    #delete the model
    model.delete()
    #create a response with a success status
    response = HttpResponse(json.dumps({'status': 'success'}),
                            mimetype="application/json")
    #add a status code to the response
    response.status_code = 203
    #return the response
    return response


def process_api(request, cls, obj_id):
    """
    The API interface for the upholstery model.
    """
    if request.method == "GET":
        params = request.GET
        if obj_id == 0:
            objs = cls.objects.all()
            try:
                objs = objs.filter(supplier_id=params["supplier_id"])
            except:
                pass
            if "last_modified" in params:
                try:
                    request_date = parser.parse(params["last_modified"])
                    data = [obj.to_dict(user=request.user) for obj in objs.filter(last_modified__gte=request_date)]
                except KeyError as e:
                    data = [obj.to_dict(user=request.user) for obj in objs]
            elif "page" in params:
                p = Paginator(objs, 50)
                page = p.page(params["page"])
                data = [obj.to_dict(user=request.user) for obj in page.object_list]
                print len(page.object_list)

            else:
                data = [obj.to_dict(user=request.user) for obj in objs]
            return HttpResponse(json.dumps(data), content_type='application/json', status=200)
        else:
            try:
                obj = cls.objects.get(pk=obj_id)
            except cls.DoesNotExist:
                return HttpResponse(content_type='aplication/json', status=404)
            return HttpResponse(json.dumps(obj.to_dict(request.user)), content_type='application/json', status=200)

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
        except Exception as e:
            print e
            return HttpResponse(status=500)

        if obj_id == 0:
            try:
                obj = cls.create(user=request.user, **data)
            except (AttributeError, ValueError) as e:
                print e
                return HttpResponse(status=500)
            return HttpResponse(json.dumps(obj.to_dict(user=request.user)), content_type="application/json", status=201)
        else:
            obj = get_object_or_404(cls, pk=obj_id)
            try:
                obj.update(user=request.user, **data)
            except AttributeError as e:
                print e
                return HttpResponse(status=500)
            return HttpResponse(json.dumps(obj.to_dict(user=request.user)), content_type="application/json", status=201)

    elif request.method == "DELETE":
            try:
                obj = cls.objects.get(pk=obj_id)
            except cls.DoesNotExist:
                return HttpResponse(content_type='aplication/json', status=404)
            obj.deleted = True
            obj.save()
            return HttpResponse("Upholstery deleted.", status=200)


def save_upload(request, filename=None):
    """
    Saves an uploaded file to disk and returns the filename
    """
    if filename is None:
        filename = "{0}{1}.jpg".format(settings.MEDIA_ROOT,time.time())
    #Save File to disk
    print request.FILES
    try:
        image = request.FILES['image']
    except MultiValueDictKeyError:
        image = request.FILES['file']
    filename = settings.MEDIA_ROOT+str(time.time())+'.jpg' 
    with open(filename, 'wb+' ) as destination:
        for chunk in image.chunks():
            destination.write(chunk)
    return filename


