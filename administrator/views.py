import json
import logging

import boto
from django.contrib.auth.models import Permission, Group, User
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from rest_framework import generics
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import boto.ses

#from administrator.models import User
from administrator.serializers import UserSerializer, GroupSerializer, PermissionSerializer
from administrator.models import Log


logger = logging.getLogger(__name__)


def log(request):
    if request.method.lower() == 'post':
        data = request.POST
    
        try:
            Log.objects.create(user=request.user, type=data['type'].upper(), message=data['message'])
        except Exception:
            pass
            
        #Send an email if log is an error
        if data['type'].lower() == 'xerror': 
            conn = boto.ses.connect_to_region('us-east-1')
            body = data['message']
            conn.send_email('no-replay@dellarobbiathailand.com',
                            u'System error for {0}'.format(request.user.username),
                            body,
                            'charliep@dellarobbiathailand.com',
                            format='html')
                            
        response = HttpResponse('Log created.', content_type='application/json; charset=utf-8')
        response.status_code = 201
        return response
        
    else:
        
        response = HttpResponse('suck it', content_type='application/json')
        response.status_code = 200 
        return response
        
    
class UserMixin(object):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    
class UserList(UserMixin, generics.ListCreateAPIView):
    pass
    

class UserDetail(UserMixin, generics.RetrieveUpdateDestroyAPIView):
    pass
    

class GroupMixin(object):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    
    
class GroupList(GroupMixin, generics.ListCreateAPIView):
    pass
    
    
class GroupDetail(GroupMixin, generics.RetrieveUpdateDestroyAPIView):
    pass
    
    
class PermissionMixin(object):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer


class PermissionList(PermissionMixin, generics.ListCreateAPIView):
    pass
    
    
class PermissionDetail(PermissionMixin, generics.RetrieveUpdateDestroyAPIView):
    pass
    
    
def get_access_key(iam, user):
    try:
        data = iam.get_all_access_keys(user.username)
        return data["list_access_keys_response"]["list_access_keys_result"]["access_key_metadata"][0]["access_key_id"]
    except IndexError:
        data = iam.create_access_key(user.username)
        return data["create_access_key_response"]["create_access_key_result"]["access_key"]["access_key_id"]
    except boto.exception.BotoServerError as e:
        print e
        iam.create_user(user.username)
        data = iam.create_access_key(user.username)
        print data
        return data["create_access_key_response"]["create_access_key_result"]["access_key"]["access_key_id"]


@login_required
#current user profile
def current_user(request):

    user = request.user

    user_data = {'firstName': user.first_name,
                 'lastName': user.last_name,
                 'permissions': [perm.split('.')[1] for perm in user.get_all_permissions()],
                 'groups': [group.name for group in user.groups.all()]}
   
    #get all the verified modules to be
    #used client side
    modules = []
    if user.has_module_perms('contacts'):
        modules.append('contacts')
    if user.has_module_perms('products'):
        modules.append('products')
    if user.has_module_perms('po'):
        modules.append('po')
    if user.has_module_perms('acknowledgements'):
        modules.append('acknowledgements')
    if user.has_module_perms('shipping'):
        modules.append('shipping')
    if user.has_module_perms('supplies'):
        modules.append('supplies')
    if user.has_module_perms('accounting'):
        modules.append('accounting')
    if user.has_module_perms('projects'):
        modules.append('projects')
    if user.has_module_perms('hr'):
        modules.append('hr')
    if user.is_superuser:
        modules.append('administrator')
    user_data['modules'] = modules
    #return data via http
    return HttpResponse(json.dumps(user_data), content_type="application/json")


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
            #Function to create dict of attributes
            def group_to_dict(group):
                return {'id': group.id,
                        'name': group.name,
                        'permissions': [{'id': perm.id,
                                         'name': perm.name} for perm in group.permissions.all()]}
                
            #Create array of items
            data = [group_to_dict(group) for group in Group.objects.all()]
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
        iam = boto.connect_iam()
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
                            'groups': [{'id': group.id,
                                        'name': group.name} for group in user.groups.all()]
                            }
                userData["aws_access_key_id"] = get_access_key(iam, user)
 
                data.append(userData)

        else:
            user = User.objects.get(id=user_id)
            data = {
                            'id': user.id,
                            'username': user.username,
                            'email': user.email,
                            'groups': [{'id': group.id, 'name': group.name} for group in user.groups.all()],
                            'first_name': user.first_name,
                            'last_name': user.last_name
                            }

            data["aws_access_key_id"] = get_access_key(iam, user)

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
        iam = boto.connect_iam()
        user = User.objects.get(id=user_id)

        #Delete access keys
        keys = iam.get_all_access_keys(user.username)
        for key in keys["list_access_keys_response"]["list_access_keys_result"]["access_key_metadata"]:
            iam.delete_access_key(key["access_key_id"], user.username)
        #Delete user from AWS
        iam.delete_user(user.username)

        user.delete()
        #build response
        response = HttpResponse(json.dumps({'status': 'success'}),
                                mimetype="application/json")
        response.status_code = 200
        #return data via http
        return response


def password(request, user_id):
    """
    Changes the password of the specified user
    """
    if request.method == "POST":
        data = json.loads(request.body)
        user = User.objects.get(id=user_id)
        print request.user.is_superuser
        if request.user.is_superuser:
            if data["new_password"] == data["repeat_new_password"]:
                user.set_password(data["new_password"])
                user.save()
                response = HttpResponse(json.dumps({'status': 'success'}),
                                        mimetype="application/json")
                response.status_code = 200
                #return data via http
                return response
            else:
                return HttpResponseBadRequest("New passwords do not match")
        else:
            if data["new_password"] == data["repeat_new_password"]:
                if authenticate(user.username, data["old_password"]):
                    user.set_password(data["new_password"])
                    user.save()
                    response = HttpResponse(json.dumps({'status': 'success'}),
                                    mimetype="application/json")
                    response.status_code = 200
                    #return data via http
                    return response
                else:
                    return HttpResponseBadRequest("Old password is incorrect")
            else:
                return HttpResponseBadRequest("New passwords do not match")
    else:
        return HttpResponseBadRequest()
