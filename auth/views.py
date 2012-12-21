# Create your views here.
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
import json
import logging

logger = logging.getLogger('EmployeeCenter');

@login_required
#current user profile
def current_user(request):
    
    user = request.user
    user_data = {
                 'firstName':user.first_name,
                 'lastName':user.last_name
                 
                 }
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

@login_required
def change_password(request):
    
    user = request.user
    data = json.loads(request.POST.get('data'))
    logger.debug(user.password)
    #Check if correct old password supplied
    if check_password(data['old'], user.password):
        
        if data['newPass'] == data['repeatPass']:
            
            user.set_password(data['newPass'])
            user.save()
            
            response = HttpResponse(json.dumps({"status":"Password Changed"}), mimetype="application/json")
            response.status_code = 200
            return response
        
        else:
            
            response = HttpResponse(json.dumps({"status":"New Passwords do not match"}), mimetype="application/json")
            response.status_code = 400
            return response
            
            
        
    else:
        
        response = HttpResponse(json.dumps({"status":"Incorrect Password"}), mimetype="application/json")
        response.status_code = 400
        return response
    
    


#Google Oauth call back
def oauth_callback(request):
    1==1
    
    
    
    
    
    