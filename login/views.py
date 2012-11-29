from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from login.models import LoginForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
import json
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
                    return HttpResponseRedirect('/index.html')
            else:
                #returns unauthenticated users
                #back to the login page
                return HttpResponseRedirect('/login')
            




def hasModule(user, data):
    
    for moduleName in data:
        
        if user.has_module_perms(moduleName):
            logger.debug(moduleName)
            logger.debug(user.has_module_perms(moduleName))
            return True
        
    return False
#build the user permissions
def buildMenu(request):
    from django.contrib.auth.models import User, Permission
    
    user = request.user
    
    menuData = {}
    
    #list of modules
    
    #supplies modules
    supplyModules = ['supplies', 'wool', 'lumber', 'fabric']
    
    
    if hasModule(user, supplyModules):
        
        categories = []
        for module in supplyModules:
            actions = []
            if user.has_perm('%s.%s_%s' %(module, 'add', module)):
                
                actions.append('Add %s' % module)
            
            if user.has_perm('%s.%s_%s' %(module, 'change', module)):
                
                actions.append('Add %s' % module)
                
            if user.has_perm('%s.%s_%s' %(module, 'delete', module)):
                
                actions.append('Add %s' % module)
            
            categories.append({'category':module, 'actions':actions})
            
            
        menuData.update({'section':'Supplies', 'categories':categories})
            
    
    return HttpResponse(json.dumps(menuData), mimetype="application/json")
            
            
            
            
            
            
            
            