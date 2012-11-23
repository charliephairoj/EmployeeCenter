from django.shortcuts import render
from django.http import HttpResponseRedirect
from login.models import LoginForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
import logging

logger = logging.getLogger('EmployeeCenter');
# Create your views here.
@login_required
def main(request):
    from django.contrib.staticfiles.views import serve



    serve(request, 'templates/auth/login.html')

    

def appLogin(request):
    #create the form object
    #to hand the inputs
    form = LoginForm()
    
    #determines if this is get request
    if request.method == "GET":
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
                    #redirects to the main page
                    return HttpResponseRedirect('/main')
            else:
                #returns unauthenticated users
                #back to the login page
                return HttpResponseRedirect('/login')