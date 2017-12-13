# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
import json
import logging

from administrator.models import User


logger = logging.getLogger('EmployeeCenter')


@login_required
#current user profile
def current_user(request):

    user = request.user

    user_data = {'firstName': user.first_name,
                 'lastName': user.last_name,
                 'permissions': [perm.split('.')[1] for perm in user.get_all_permissions()]}
   
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
    if user.has_module_perms('equipment'):
        modules.append('equipment')
    if user.is_superuser:
        modules.append('administrator')
    user_data['modules'] = modules
    #return data via http
    return HttpResponse(json.dumps(user_data), content_type="application/json")


@login_required
def change_password(request):
    user = request.user

    data = json.loads(request.body)

    #Check if correct old password supplied
    if user.is_superuser:
        if data["new_password"] == data["repeat_new_password"]:
            user = User.objects.get(id=data["user_id"])
            user.set_password(data["new_password"])
            user.save()
            response = HttpResponse(json.dumps({'status': 'success'}),
                                    content_type="application/json")
            response.status_code = 200
            #return data via http
            return response
        else:
            return HttpResponseBadRequest("New passwords do not match")
    else:
        if check_password(data['old'], user.password):
            if data['newPass'] == data['repeatPass']:
                user.set_password(data['newPass'])
                user.save()
                response = HttpResponse(json.dumps({"status": "Password Changed"}),
                                        content_type="application/json")
                response.status_code = 200
                return response
            else:
                response = HttpResponse(json.dumps({"status": "New Passwords do not match"}),
                                        content_type="application/json")
                response.status_code = 400
                return response
        else:
            response = HttpResponse(json.dumps({"status": "Incorrect Password"}),
                                    content_type="application/json")
            response.status_code = 400
            return response


@login_required
#Google Oauth call back
def oauth_callback(request):
    from oauth2client.client import OAuth2WebServerFlow
    from auth.models import CredentialsModel
    from oauth2client.django_orm import Storage
    #Get query code from auth request
    code = request.GET.get('code')
    #create flow object
    flow = OAuth2WebServerFlow(client_id='940056909424-57b143selist3s7uj8rnpcmt7f2s0g7u.apps.googleusercontent.com',
                           client_secret='mgHATY9kYzp3HEHg2xKrYzmh',
                           scope=['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/drive'],
                           redirect_uri='http://localhost:8000/oauth2callback')
    #retrieve and store credentials
    credentials = flow.step2_exchange(code)
    storage = Storage(CredentialsModel, 'id', request.user, 'credential')
    storage.put(credentials)
    #mark user has having been validated
    user = request.user
    user_profile = user.get_profile()
    user_profile.google_validated = True
    user_profile.save()
    return HttpResponseRedirect('/index.html')
