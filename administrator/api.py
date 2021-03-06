"""
API Classes for all Administrator models
"""
import logging
import json
import time

from tastypie.resources import ModelResource
from tastypie.authorization import DjangoAuthorization
from tastypie.exceptions import Unauthorized
from django.conf.urls import url
from django.contrib.auth.models import User, Group, Permission
from django.db.models import Q

from administrator.validation import UserValidation
from media.models import S3Object, Employee
from utilities.http import save_upload


logger = logging.getLogger(__name__)


class UserResource(ModelResource):
    
    class Meta:
        object_class = User
        queryset = User.objects.all()
        resource_name = 'user'
        authorization = DjangoAuthorization()
        always_return_data = True
        validation = UserValidation()
        #allowed_methods = ['post', 'get', 'put']
        fields = ['username', 'email', 'first_name', 'last_name', 'id', 'last_login']
        
    def prepend_urls(self):
        """
        Add additional API points
        """
        return [url(r"^{0}/image$".format(self._meta.resource_name), self.wrap_view('process_image')),
                url(r"^{0}/(?P<pk>\d+)/change_password$".format(self._meta.resource_name), self.wrap_view('change_password'))]
        
    def hydrate(self, bundle):
        """
        implements the hydrate for the User
        """
        try:
            client_groups = set([group['id'] for group in bundle.data['groups']]) if "groups" in bundle.data else set()
            server_groups = set([group.id for group in bundle.obj.groups.all()])
           
            #Adds new groups to the user
            for group_id in client_groups.difference(server_groups):
                group = Group.objects.get(pk=group_id)
                bundle.obj.groups.add(group)
                logger.info("User '{0}' added to '{1}' group.".format(bundle.obj.username, 
                                                                      group.name))
                
            #Removes groups from the user
            for group_id in server_groups.difference(client_groups):
                group = Group.objects.get(pk=group_id)
                bundle.obj.groups.remove(group)
                logger.info("User '{0}' removed from '{1}' group.".format(bundle.obj.username, 
                                                                          group.name))
        except ValueError:
            pass
        
        try:
            bundle.obj.employee.telephone = bundle.data['telephone']
        except KeyError as e:
            logger.warn(e)
        except AttributeError:
            logger.critical(e)
        
        #Updates the image
        try:
            bundle.obj.employee.image = S3Object.objects.get(pk=bundle.data['image']['id'])
        except KeyError as e:
            pass
        
        #Save all employee profile updates
        try:
            bundle.obj.employee.save()
        except Employee.DoesNotExist as e:
            pass
        
        return bundle
    
    def dehydrate(self, bundle):
        """
        Implements a dehydrate method
        """
        #List all permissions from groups
        """
        permissions = [{'id': p.id,
                        'description': p.name,
                        'name': p.name} for p 
                        in Permission.objects.filter(group__user__id=bundle.data['id'])]
        bundle.data['permissions'] = permissions
        """
        #List all groups
        groups = [{'id': g.id,
                   'description': g.name,
                   'name': g.name} for g in bundle.obj.groups.all()]
        bundle.data['groups'] = groups
            
        #Remove the password
        if "password" in bundle.data:
            del bundle.data["password"]
            
        try:
            bundle.data['telephone'] = bundle.obj.employee.telephone
        except Exception as e:
            logger.warn(e)
            
        try:
            image = bundle.obj.employee.image
            bundle.data['image'] = {'id': image.id,
                                    'url': image.generate_url()}
        except Exception as e:
            logger.warn(e)
        
        return bundle
    
    def obj_create(self, bundle, **kwargs):
        """
        Implements the obj_create method
        """
        logger.info("Creating a new user...")
        try:
            bundle.obj = User.objects.create_user(bundle.data['username'],
                                                  bundle.data['email'],
                                                  bundle.data['password'])
            bundle.obj.first_name = bundle.data['first_name']
            bundle.obj.last_name = bundle.data['last_name']
            bundle.obj.save()
            logger.info("User '{0}' created.".format(bundle.obj.username))
        except Exception as e:
            logger.debug(e)
            
        #Create the user employee profile
        employee_profile = Employee()
        employee_profile.user = bundle.obj
        
        #try adding image
        try:
            employee_profile.image = S3Object.objects.get(pk=bundle.data['image']['id'])
        except KeyError:
            pass
        
        employee_profile.save()
        
        #Add user groups
        if "groups" in bundle.data:
            for g in bundle.data['groups']:
                try:
                    group = Group.objects.get(g['id'])
                    bundle.obj.groups.add(group)
                    logger.info("User '{0}' added to '{1}' group.".format(bundle.obj.username,
                                                                          group.name))
                except Group.DoesNotExist:
                    pass
            
        return bundle
    
    def process_image(self, request, **kwargs):
        """
        Receives an image and processes it
        """
        filename = save_upload(request)
        
        image = S3Object.create(filename,
                        "user/image/{0}.jpg".format(time.time()),
                        "media.dellarobbiathailand.com")
        #set Url, key and bucket
        data = {'url': image.generate_url(),
                "id": image.id,
                'key': image.key,
                'bucket': image.bucket}
        
        return self.create_response(request, data)
    
    def change_password(self, request, **kwargs):
        """
        Change the password of the user with 
        the specified pk
        """
        user = self._meta.queryset.get(pk=kwargs['pk'])
        logger.debug(user)
        data = json.loads(request.body)
        
        try:
            new_pass = data['new_password']
            repeat_new_pass = data['repeat_new_password']
        except (KeyError, TypeError) as e:
            raise
           
        if new_pass != repeat_new_pass:
            raise ValueError("Passwords do not match")
        
        user.set_password(new_pass)
        user.save()
        return self.create_response(request, {})
    

class GroupResource(ModelResource):
    
    class Meta:
        always_return_data = True
        authorization = DjangoAuthorization()
        queryset = Group.objects.all()
        resource_name = 'group'
        
    def hydrate(self, bundle):
        """
        Implements the hydrate method to set the data of the obj
        before it is saved
        """
        try:
            client_perms = set([p['id'] for p in bundle.data['permissions']]) if "permissions" in bundle.data else set()
            server_perms = set([p.id for p in bundle.obj.permissions.all()]) 
            
            #Add permissions to the group
            for perm_id in client_perms.difference(server_perms):
                bundle.obj.permissions.add(Permission.objects.get(pk=perm_id))
                
            #Remove permission from the group
            for perm_id in server_perms.difference(client_perms):
                bundle.obj.permissions.remove(Permission.objects.get(pk=perm_id))
        except ValueError:
            pass
        
        return bundle
            
    def dehydrate(self, bundle):
        """
        Implements the dehydrate method to modify the data to be
        returned to the client
        """
        
        permissions = [{'id': p.id,
                        'name': p.name} for p in bundle.obj.permissions.all()]
        bundle.data['permissions'] = permissions
        
        return bundle
        
    def obj_create(self, bundle, **kwargs):
        """
        Implements the obj_create method
        """
        logger.info("Creating a new group...")
        bundle = super(GroupResource, self).obj_create(bundle, **kwargs)
        logger.info("Group '{0}' created.".format(bundle.obj.name))
        
        #Add permission to the group
        if "permissions" in bundle.data:
            for p in bundle.data['permissions']:
                try:
                    perm = Permission.objects.get(pk=p['id'])
                    bundle.obj.permissions.add(perm)
                    logger.info("Permission '{0}' granted to '{1}' group.".format(perm.name,
                                                                                  bundle.obj.name))
                except Permission.DoesNotExist:
                    pass
        
        return bundle
    

class PermissionResource(ModelResource):
     
    class Meta:
        queryset = Permission.objects.all()
        resource_name = 'permission'
        