import json
import logging

from django.contrib.auth.models import Permission, Group, User
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required

from auth.models import UserProfile

logger = logging.getLogger('EmployeeCenter')


#Deals with the permission
@login_required
def permission(request, permission_id='0'):

    if request.method == "GET":
        #Create the array
        data = []
        #Loop to access all models
        for perm in Permission.objects.all():
            #create dict with permissions
            permData = {'id': perm.id, 'name': perm.name,
                        'app': perm.content_type.app_label}
            #Add raw data to array
            data.append(permData)
        #return data via http
        return HttpResponse(json.dumps(data), mimetype="application/json")


@login_required
def get_group_data(request, group):
    data = {'id': group.id, 'name': group.name, 'permissions': []}
    for perm in group.permissions.all():
        data["permissions"].append({'id': perm.id, 'name': perm.name,
                                    'app': perm.content_type.app_label})
    return data


#Deals with the Groups
@login_required
def group(request, group_id=0):
    if request.method == "GET":
        if group_id == 0:
            #Create the array
            data = []
            permData = []
            #Loop to access all models
            for group in Group.objects.all():
                for perm in group.permissions.all():
                    permData.append({'id': perm.id,
                                     'name': perm.name})
                #create dict with permissions
                groupData = {'id': group.id, 'name': group.name,
                             'permissions': permData}
                #Add raw data to array
                data.append(groupData)
            #return data via http
            return HttpResponse(json.dumps(data), mimetype="application/json")
        else:
            group = Group.objects.get(id=group_id)
            data = get_group_data(request, group)
            return HttpResponse(json.dumps(data), mimetype="application/json")

    elif request.method == "POST":
        #get the data
        data = json.loads(request.body)
        if group_id == 0:
            group = Group()
        else:
            group = Group.objects.get(id=group_id)
        #assign properties
        if "name" in data:
            group.name = data["name"]
        #check if has permissions
        if "permissions" in data:
            #loop through permissions
            for permData in data["permissions"]:
                if "status" in permData:
                    if permData["status"] == "add":
                        perm = Permission.objects.get(id=permData["id"])
                        group.permissions.add(perm)
                    if permData["status"] == "delete":
                        perm = Permission.objects.get(id=permData["id"])
                        group.permissions.remove(perm)
        #save the group
        group.save()
        #merge with data for output
        data = get_group_data(request, group)
        #build response
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 201
        #return data via http
        return response
    elif request.method == "PUT":
        group = Group.objects.get(id=group_id)
        request.method = "POST"
        request._load_post_and_files()
        logger.debug(request.POST)
        data = json.loads(request.POST.get('data'))
        if "permissions" in data:
            for perm in data['permissions']:
                #if group.permissions.exists(id=perm['id'])==False:
                group.permissions.add(Permission.objects.get(id=perm['id']))
    elif request.method == "DELETE":
        group = Group.objects.get(id=group_id)
        group.delete()
        response = HttpResponse(json.dumps({'status': 'success'}),
                                mimetype="application/json")
        response.status_code = 201
        #return data via http
        return response


#Deals with User
@login_required
def user(request, user_id=0):
    if request.method == "GET":
        if user_id == 0:
            data = []
            for user in User.objects.all():
                #permissionData = []
                groupData = []
                #for perm in user.user_permssions.all():
                    #permissionData.append({'id':perm.id, 'name':perm.name})
                for group in user.groups.all():
                    groupData.append({'id': group.id,
                                      'name': group.name})
                userData = {
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'id': user.id,
                            'username': user.username,
                            'email': user.email,
                            'last_login': user.last_login.isoformat(),
                            'groups': groupData
                            #'permissions':permissionData
                            }
                data.append(userData)

        else:
            user = User.objects.get(id=user_id)
            groupData = []
            for group in user.groups.all():
                groupData.append({'id': group.id, 'name': group.name})
            data = {
                            'id': user.id,
                            'username': user.username,
                            'email': user.email,
                            'groups': groupData,
                            'first_name': user.first_name,
                            'last_name': user.last_name
                            }
        #build response
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 200
        #return data via http
        return response

    elif request.method == "POST":
        #get data
        data = json.loads(request.body)
        if user_id == 0:
            user = User.objects.create_user(data['username'], data['email'],
                                            data['password'])
            user.is_staff = True
            user.save()
            #Create the User Profile
            user_profile = UserProfile()
            user_profile.user = user
            user_profile.save()
        else:
            user = User.objects.get(id=user_id)
        if "last_name" in data:
            user.last_name = data["last_name"]
        if "first_name" in data:
            user.first_name = data["first_name"]
        if "email" in data:
            user.email = data["email"]
        if "username" in data:
            user.username = data["username"]
        if "groups" in data:
            for groupData in data["groups"]:
                if "status" in groupData:
                    if groupData["status"] == "add":
                        group = Group.objects.get(id=groupData["id"])
                        user.groups.add(group)
                    if groupData["status"] == "delete":
                        group = Group.objects.get(id=groupData["id"])
                        user.groups.remove(group)
        #save the user
        user.save()
        #build response
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 200
        #return data via http
        return response

    elif request.method == "PUT":
        #change to put
        request.method = "POST"
        request._load_post_and_files()
        # Load data
        data = json.loads(request.POST.get('data'))
        request.method = "PUT"
        user = User.objects.get(id=user_id)
        if "firstName" in data:
            user.first_name = data["firstName"]
        if "lastName" in data:
            user.last_name = data["lastName"]
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

    elif request.method == "DELETE":
        user = User.objects.get(id=user_id)
        user.delete()
        #build response
        response = HttpResponse(json.dumps({'status': 'success'}),
                                mimetype="application/json")
        response.status_code = 200
        #return data via http
        return response
