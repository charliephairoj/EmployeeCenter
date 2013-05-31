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




# Create your views here.
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
        print request
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
                """
                    #checks if authenticated for google
                    if user_profile.google_validated == False:
                        return HttpResponseRedirect('/auth')
                    
                    else:
                        
                        return HttpResponseRedirect('/')"""
            else:
                #returns unauthenticated users
                #back to the login page
                return HttpResponseRedirect('/login')
            

#Logs user out
def logout(request):
    
    from django.contrib.auth import logout
    
    logout(request)
    
    return HttpResponseRedirect('/')

#Deals with google auth
"""
def auth_flow(request):
    flow = OAuth2WebServerFlow(client_id='940056909424-57b143selist3s7uj8rnpcmt7f2s0g7u.apps.googleusercontent.com',
                           client_secret='mgHATY9kYzp3HEHg2xKrYzmh',
                           scope=['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/drive'],
                           redirect_uri='http://data.dellarobbiathailand.com/oauth2callback')
    
    auth_uri = flow.step1_get_authorize_url()
    
    user = request.user
    user_profile = user.get_profile()
    user_profile.flow = flow
    user_profile.save()
    
    return HttpResponseRedirect(auth_uri)

def has_module(user, data):
    
    for module_name in data:
        
        if user.has_module_perms(module_name):
            
            return True
        
    return False
#build the user permissions
def buildMenu(request):
    from django.contrib.auth.models import User, Permission
    
    user = request.user
    
    menu_data = {}
    
    #list of modules
    
    #supplies modules
    supply_modules = ['supplies', 'wool', 'lumber', 'fabric']
    
    
    if has_module(user, supply_modules):
        
        categories = []
        for module in supply_modules:
            actions = []
            if user.has_perm('%s.%s_%s' %(module, 'add', module)):
                
                actions.append('Add %s' % module)
            
            if user.has_perm('%s.%s_%s' %(module, 'change', module)):
                
                actions.append('Add %s' % module)
                
            if user.has_perm('%s.%s_%s' %(module, 'delete', module)):
                
                actions.append('Add %s' % module)
            
            categories.append({'category':module, 'actions':actions})
            
            
        menu_data.update({'section':'Supplies', 'categories':categories})
            
    
    return HttpResponse(json.dumps(menu_data), mimetype="application/json")
            
            
            
            
"""
            
            
            