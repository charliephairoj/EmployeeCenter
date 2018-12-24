


import json
import logging
import os

from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt, csrf_protect
from django.contrib.staticfiles.views import serve
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.utils.safestring import mark_safe
from django.shortcuts import render_to_response
from oauth2client.contrib import xsrfutil
from oauth2client.client import flow_from_clientsecrets
#from oauth2client.contrib.django_orm import Storage

from auth.views import current_user
from login.models import LoginForm, PasswordResetForm
from administrator.models import CredentialsModel, Storage, User



logger = logging.getLogger(__name__)

CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secrets.json')

# List of scopes to request access to
scopes = 'https://www.googleapis.com/auth/calendar'
scopes += ' https://www.googleapis.com/auth/calendar.readonly'
scopes += ' https://www.google.com/m8/feeds/'
scopes += ' https://www.googleapis.com/auth/drive.appdata'
scopes += ' https://www.googleapis.com/auth/drive.file'
FLOW = flow_from_clientsecrets(
    CLIENT_SECRETS,
    scope=scopes,
    redirect_uri='https://employee.alineagroup.co/oauth2callback')
    #redirect_uri='http://localhost:8000/oauth2callback')



@csrf_protect
@login_required
@ensure_csrf_cookie
def main(request):
    if request.user.web_ui_version.lower() == 'v2':
        #return render(request, '/home/django_worker/frontend/dist/index.html')

        return render(request, '/home/webserver-data/athena/index.html')
    else:
        return render(request, '/home/webserver-data/frontend/dist/index.html')

@login_required
def password_reset(request):
    
    #determines if this is get request
    if request.method == "GET":
        """Determines if the user is authenticated.
        Authenticated users are served the index page
        while anonymous users are served the login page"""
        if request.user.is_authenticated():
            
            form = PasswordResetForm()
            return render(request, 'password_reset.html', {'form':form})

        else:
            return HttpResponseRedirect('/login')


    #what to do with a post request
    elif request.method == "POST":
        logger.debug(request.POST)
        #initialize form with post data
        form = PasswordResetForm(request.POST)
        #check if form is valid
        logger.debug(form.is_valid())
        logger.debug(form.errors)
        if form.is_valid():
            clean_password = form.cleaned_data['password']
            clean_repeat_password = form.cleaned_data['repeat_password']

            if clean_password == clean_repeat_password:
                user = request.user

                user.set_password(clean_password)
                user.reset_password = False
                user.save()
                
                logger.debug(clean_password)
                logger.debug(clean_repeat_password)

                return HttpResponseRedirect('/')
        
            else:
                form = PasswordResetForm()

                return render(request, 'password_reset.html', {'form':form})
            
        else:

            form = PasswordResetForm()

            return render(request, 'password_reset.html', {'form':form})


@login_required
def check_google_authenticated(request):
    storage = Storage(CredentialsModel, 'id', request.user, 'credential')
    credentials = storage.get()

    if credentials is None or credentials.invalid is True:
        FLOW.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY,
                                                       request.user)
        FLOW.params['access_type'] = 'offline'
        authorize_url = FLOW.step1_get_authorize_url()

        logger.debug(authorize_url)

        return HttpResponseRedirect(authorize_url)


    else:
        return HttpResponseRedirect('/main')


@csrf_exempt
def app_login(request):
    #create the form object
    #to hand the inputs
    form = LoginForm()

    #determines if this is get request
    if request.method == "GET":
        """Determines if the user is authenticated.
        Authenticated users are served the index page
        while anonymous users are served the login page"""
        if request.user.is_authenticated():
            #Gets user profile to do checks


            #Only require google login if not inventory
            if request.user.first_name.lower() != 'inventory':

                return check_google_authenticated(request)

            return HttpResponseRedirect('/main')

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

            cleanUsername = form.cleaned_data['username']
            cleanPassword = form.cleaned_data['password']
            
            user = authenticate(username=cleanUsername,
                                password=cleanPassword)

            #checks whether user authennticated
            if user is not None:
                #checks if user is still active
                if user.is_active:
                    
                    #login the user
                    login(request, user)

                    #Check if the password needs to be reset
                    if user.reset_password:
                        return HttpResponseRedirect('/password-reset')

                    #Only require google login if not inventory
                    if user.first_name.lower() != 'inventory':
                        #return HttpResponseRedirect('/main')

                        return check_google_authenticated(request)

                    #Gets user profile to do checks
                    return HttpResponseRedirect('/main')

            return HttpResponseRedirect('/')

        else:

            logger.warn(form.__dict__)
            
            #create a new login form
            form = LoginForm()
            return render(request, 'login.html', {'form':form})

    else:
        #create a new login form
        form = LoginForm()
        return render(request, 'login.html', {'form':form})


@login_required
def auth_return(request):
    if not xsrfutil.validate_token(settings.SECRET_KEY,
                                   str(request.GET['state']),
                                   request.user):

        return  HttpResponseBadRequest()

    credential = FLOW.step2_exchange(request.GET)
    storage = Storage(CredentialsModel, 'id', request.user, 'credential')
    storage.put(credential)
    return HttpResponseRedirect("/main")


#Logs user out
def logout(request):
    from django.contrib.auth import logout
    logout(request)
    return HttpResponseRedirect('/')
