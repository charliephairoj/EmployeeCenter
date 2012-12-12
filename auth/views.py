# Create your views here.
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
import json

#current user profile
def current_user(request):
    
    user = request.user
    user_data = {}
    data = []
    #creates the permissions data
    #that will be used client side
    permissions = user.get_all_permissions()
    for permission in permissions:
        permission = permission.split('.')
        code = permission[1]
        #permObj = Permission.objects.get(codename=perm, content_type=content_type)
        data.append(code)
        
    user_data["permissions"] = data
    #get all the verified modules to be 
    #used client side
    modules = []
    if user.has_module_perms('contacts'): modules.append('contacts')
    if user.has_module_perms('po'): modules.append('orders')
    if user.has_module_perms('supplies'): modules.append('supplies')
    if user.is_superuser: modules.append('administrator')
    user_data['modules'] = modules
    #return data via http 
    return HttpResponse(json.dumps(user_data), mimetype="application/json")
