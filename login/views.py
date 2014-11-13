


import json
import logging

from django.shortcuts import render
from django.contrib.staticfiles.views import serve
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils.safestring import mark_safe

from auth.views import current_user
from login.models import LoginForm


logger = logging.getLogger(__name__)


@login_required
def main(request):
    serve(request, 'templates/auth/login.html')


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

            #Get User data
            user_data = {}
            jsonStr = mark_safe(json.dumps(user_data))
            #checks if authenticated for google
            """
            if user_profile.google_validated == False:

                #return HttpResponseRedirect('/auth')
                #return serve(request, 'index.html', settings.STATIC_ROOT)
                return render(request, 'home.html', {'user_data': jsonStr})
            else:
                return render(request, 'home.html', {'user_data': jsonStr})
            """
            #render(request, 'home.html', settings.STATIC_ROOT, {'user_data': jsonStr})
            logger.debug(settings.TEMPLATE_DIRS[0])
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

                    #Gets user profile to do checks
                    url = '/'#'http://localhost:9001/index.html' if settings.DEBUG else '/'
                    return HttpResponseRedirect(url)

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


#Logs user out
def logout(request):
    from django.contrib.auth import logout
    logout(request)
    return HttpResponseRedirect('/')


