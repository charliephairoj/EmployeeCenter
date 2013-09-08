from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from oauth2client.client import OAuth2WebServerFlow

from login.models import LoginForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
import json
from django.utils.log import getLogger
from django.utils.safestring import mark_safe

from auth.views import current_user


@login_required
def main(request):
    from django.contrib.staticfiles.views import serve
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
            user_data = current_user(request)
            jsonStr = mark_safe(json.dumps(user_data))
            #checks if authenticated for google
            """
            if user_profile.google_validated == False:

                #return HttpResponseRedirect('/auth')
                #return serve(request, 'index.html', settings.STATIC_ROOT)
                return render(request, 'home.html', {'user_data': jsonStr})
            else:
                #return serve(request, 'index.html', settings.STATIC_ROOT)#HttpResponseRedirect('index.html')
                return render(request, 'home.html', {'user_data': jsonStr})
            """
            return render(request, 'home.html', {'user_data': jsonStr})

        else:
            #logout the request
            logout(request)
            #create a new login form
            form = LoginForm()
            return render(request, 'auth/login.html', {'form':form})
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
                    return HttpResponseRedirect('/')

                else:
                    return HttpResponseRedirect('/login')

            else:
                #returns unauthenticated users
                #back to the login page
                return HttpResponseRedirect('/login')
        else:
            return HttpResponseRedirect('/login')


#Logs user out
def logout(request):
    from django.contrib.auth import logout
    logout(request)
    return HttpResponseRedirect('/')


