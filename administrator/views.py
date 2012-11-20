from wool.models import Wool
from django.contrib.auth.models import Permission, Group, User
import json
from django.http import HttpResponseRedirect, HttpResponse
import logging

logger = logging.getLogger('EmployeeCenter');
#Deals with the permission
def permission(request, permissionID = '0'):
    
    if request.method == "GET":
        #Create the array
        data = []
        #Loop to access all models
        for perm in Permission.objects.all():
            #create dict with permissions
            permData = {'id':perm.id, 'name':perm.name}
            #Add raw data to array
            data.append(permData) 
            
           
        #return data via http 
        return HttpResponse(json.dumps(data), mimetype="application/json")
        

#Deals with the Groups
def group(request, groupID = '0'):
    
    if request.method == "GET":
        
        if groupID == '0':
            #Create the array
            data = []
            permData = []
            #Loop to access all models
            for group in Group.objects.all():
                
                for perm in group.permissions.all():
                    permData.append({'id':perm.id, 'name':perm.name})
                #create dict with permissions
                groupData = {'id':group.id, 'name':group.name, 'permissions':permData}
                #Add raw data to array
                data.append(groupData) 
                
            #return data via http 
            return HttpResponse(json.dumps(data), mimetype="application/json")
        
        else:
            
            logger.debug(groupID)
            permData = []
            group = Group.objects.get(id=groupID)
            for perm in group.permissions.all():
                permData.append({'id':perm.id, 'name':perm.name})
                
            data = {'id':group.id, 'name':group.name, 'permissions':permData}
    
            #return data via http 
            return HttpResponse(json.dumps(data), mimetype="application/json")
        
    elif request.method == "POST":
        
        #get the data
        data = json.loads(request.POST.get('data'))
        #create the new group
        group = Group()
        #assign properties
        if "name" in data:group.name = data["name"]
        #saves the group
        #to create a key for permissions
        group.save()
        #check if has permissions
        if "permissions" in data:
            #loop through permissions
            for permData in data["permissions"]:
                #get permission
                permission = Permission.objects.get(id=permData['id'])
                #add permission to the group
                group.permissions.add(permission)
        #save the group
        group.save()
        
        #merge with data for output
        data.update({'id':group.id})
        #build response
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 201
        #return data via http 
        return response
    
    elif request.method == "PUT":
        
        group = Group.objects.get(id=groupID)
        
        request.method = "POST"
        request._load_post_and_files();
        logger.debug(request.POST)
        
        data = json.loads(request.POST.get('data'))
        
        if "permissions" in data:
            for perm in data['permissions']:
                #if group.permissions.exists(id=perm['id'])==False:
                group.permissions.add(Permission.objects.get(id=perm['id']))
                    
                    
    
    elif request.method == "DELETE":
        
        group = Group.objects.get(id=groupID)
        
        group.delete()
        
        response = HttpResponse(json.dumps({'status':'success'}), mimetype="application/json")
        response.status_code = 201
        #return data via http 
        return response
        
        
        
        
#Deals with User
def user(request):
    
    if request.method == "GET":
        
        data = []
        
        for user in User.objects.all():
            #permissionData = []
            groupData = []
            
            #for perm in user.user_permssions.all():
                
                #permissionData.append({'id':perm.id, 'name':perm.name})
                
            for group in user.groups.all():
                groupData.append({'id':group.id, 'name':group.name})
                #for perm in group.permissions.all():
                    #permissionData.append({'id':perm.id, 'name':perm.name})
                    
            userData = {
                        'id':user.id,
                        'username':user.username,
                        'email': user.email,
                        'groups':groupData
                        #'permissions':permissionData
                        }
            
            data.append(userData)
            
            
        #build response
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 200
        #return data via http 
        return response
            
    elif request.method == "POST":
        
        #get data
        data = json.loads(request.POST.get('data'))
        logger.debug(data)
        if "username" in data and "email" in data and "password" in data:
                    
            user = User.objects.create_user(data['username'], data['email'], data['password'])
            user.is_staff = True
            
            if "firstName" in data:user.first_name = data["firstName"]
            if "lastName" in data: user.last_name = data["last_name"] 
            
            if "groups" in data:
                for group in data["groups"]:
                    
                    user.groups.add(Group.objects.get(id=group['id']))
            
            #save the user
            user.save()
        
        #build response
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 200
        #return data via http 
        return response
            