


import json
import logging
import os

from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt, csrf_protect
from django.contrib.staticfiles.views import serve
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils.safestring import mark_safe
from django.shortcuts import render_to_response
from oauth2client import xsrfutil
from oauth2client.client import flow_from_clientsecrets
from oauth2client.django_orm import Storage

from auth.views import current_user
from login.models import LoginForm
from administrator.models import CredentialsModel



logger = logging.getLogger(__name__)

CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secrets.json')

FLOW = flow_from_clientsecrets(
    CLIENT_SECRETS,
    scope='https://www.googleapis.com/auth/plus.me',
    redirect_uri='http://localhost:8000/oauth2callback')
    
    
@csrf_protect
@login_required
@ensure_csrf_cookie
def main(request):
    serve(request, 'templates/auth/login.html')


@csrf_exempt
@ensure_csrf_cookie
def app_login(request):
    #create the form object
    #to hand the inputs
    form = LoginForm()

    logger.debug(request.method);
    #determines if this is get request
    if request.method == "GET":
        """Determines if the user is authenticated.
        Authenticated users are served the index page
        while anonymous users are served the login page"""
        if request.user.is_authenticated():
            #Gets user profile to do checks

            #Get User data
            user_data = {}
            jsonStr = mark_safe(json.dumps(user_data))
            #checks if authenticated for google
            
            #render(request, 'home.html', settings.STATIC_ROOT, {'user_data': jsonStr})
            return render(request, 'index.html')

            #return render(request, 'home.html', {'user_data': jsonStr})

        else:
            #logout the request
            logout(request)
            #create a new login form
            form = LoginForm()
            return render(request, 'login.html', {'form':form})
    #what to do with a post request
    elif request.method == "POST":
        #initialize form with post data
        form = LoginForm(request.POST)
        #check if form is valid
        if form.is_valid():
            #gets the clean password and
            #clean username
            cleanUsername = form.cleaned_data['username']
            cleanPassword = form.cleaned_data['password']
            #authenticate the user
            #if not authenticated user is None
            user = authenticate(username=cleanUsername, password=cleanPassword)

            #checks whether user authennticated
            if user is not None:
                #checks if user is still active
                if user.is_active:

                    #login the user
                    login(request, user)
                    
                    storage = Storage(CredentialsModel, 'id', request.user, 'credential')
                    credential = storage.get()
                    
                    if credential is None or credential.invalid == True:
                        FLOW.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY,
                                                                       request.user)
                        authorize_url = FLOW.step1_get_authorize_url()
                        return HttpResponseRedirect(authorize_url)
                        
                    else:
                        http = httplib2.Http()
                        http = credential.authorize(http)
                        service = build("plus", "v1", http=http)
                        activities = service.activities()
                        activitylist = activities.list(collection='public',
                                                       userId='me').execute()
                        logging.info(activitylist)

                        return render_to_response('plus/welcome.html', {
                                    'activitylist': activitylist,
                                    })

                    #Gets user profile to do checks
                    #url = '/'#'http://localhost:9001/index.html' if settings.DEBUG else '/'
                    #return HttpResponseRedirect(url)

                else:
                    logger.debug('User is not active')
                    return HttpResponseRedirect('/login')

            else:
                logger.debug('User is None')
                #returns unauthenticated users
                #back to the login page
                return HttpResponseRedirect('/login')
        else:
            logger.debug('Form not valid')
            return HttpResponseRedirect('/login')


@login_required
def auth_return(request):
    if not xsrfutil.validate_token(settings.SECRET_KEY, 
                                   str(request.GET['state']), 
                                   request.user):
                                   
        return  HttpResponseBadRequest()
  
    credential = FLOW.step2_exchange(request.GET)
    storage = Storage(CredentialsModel, 'id', request.user, 'credential')
    storage.put(credential)
    return HttpResponseRedirect("/")


#Logs user out
def logout(request):
    from django.contrib.auth import logout
    logout(request)
    return HttpResponseRedirect('/')


