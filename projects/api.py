"""
API file for projects
"""
from decimal import Decimal
from datetime import datetime, timedelta
import time
import logging
import json
import re

from django.db.models import Q
from django.conf.urls import url
from tastypie import fields
from tastypie.resources import ModelResource
from tastypie.authorization import DjangoAuthorization
from tastypie.exceptions import Unauthorized

from projects.models import Project, ProjectSupply, Room
from supplies.models import Supply


logger = logging.getLogger(__name__)


class ProjectResource(ModelResource):
    rooms = fields.ToManyField('projects.api.RoomResource', 'rooms', 
                               readonly=True, full=True, null=True)
    customer = fields.ToOneField('contacts.api.CustomerResource', 'customer', null=True,
                                 readonly=True, full=True)
    class Meta:
        queryset = Project.objects.all()
        resource_name = 'project'
        always_return_data = True
        authorization = DjangoAuthorization()
        
    def prepend_urls(self):
        return [
                url(r"^{0}/(?P<pk>\d+)/supply$".format(self._meta.resource_name), self.wrap_view('add_supply')),
               ]
    
    def apply_filters(self, request, applicable_filters):
        obj_list = super(ProjectResource, self).apply_filters(request, applicable_filters)
        
        if request.GET.has_key('q'):
            query = request.GET.get('q')
            obj_list = obj_list.filter(Q(codename__icontains=query))
        
        return obj_list
        
    def dehydrate(self, bundle):
        """
        Custom Dehydration for the project resource
        """
        #Dehydrate the supply
        bundle.data['supplies'] = [self.dehydrate_supply(ps) for ps in ProjectSupply.objects.filter(project=bundle.obj)]

        return bundle
        
    def obj_update(self, bundle, **kwargs):
        """
        Custom hydrate method before the resource is saved to the server
        """
        
        bundle = super(ProjectResource, self).obj_update(bundle, **kwargs)
        
        #Remove supplies deleted by the client
        client_ids = set([supp['id'] for supp in bundle.data['supplies']])
        server_ids = set([supp.id for supp in bundle.obj.supplies.all()])
        for supp_id in server_ids.difference(client_ids):
            ProjectSupply.objects.get(supply_id=supp_id, 
                                      project=bundle.obj).delete()
        
        #Update all supplies    
        for supply in bundle.data['supplies']:
            self._hydrate_supply(bundle, supply)
            
        return bundle
        
    def add_supply(self, request, **kwargs):
        """
        Adds a new supply to the project
        """
        if request.method == "POST":
            #Get the project
            project = Project.objects.get(pk=kwargs['pk'])
        
            supply_data = json.loads(request.body)
            supply = Supply.objects.get(pk=supply_data['id'])
        
            try:
                ProjectSupply.objects.get(supply=supply, project=project)
            except ProjectSupply.DoesNotExist:
                ps = ProjectSupply(supply=supply, project=project)
                ps.save()
            
            return self.create_response(request, supply_data)
    
    def _hydrate_supply(self, bundle, supply_obj):
        """
        Creates or updates an supply for the project
        """
        try:
            project_supply = ProjectSupply.objects.get(project=bundle.obj,
                                                       supply_id=supply_obj['id'])
        except ProjectSupply.DoesNotExist as e:
            project_supply = ProjectSupply()
            project_supply.project = bundle.obj
            project_supply.supply = Supply.objects.get(pk=supply_obj['id'])
            
        for field in project_supply._meta.get_all_field_names():
            if field in supply_obj and field not in ['id', 'project', 'supply']:
                setattr(project_supply, field, supply_obj[field]) 
                               
        project_supply.save()
                                       
    def dehydrate_supply(self, project_supply):
        """
        Extract the supply information as a dictionary
        """
        data = {'id': project_supply.supply.id,
                'description': project_supply.supply.description,
                'quantity': project_supply.quantity}
        if project_supply.supply.image:
            data['image'] = {'url': project_supply.supply.image.generate_url()}
            
        return data
    
        

class RoomResource(ModelResource):
        
    project = fields.ToOneField('projects.api.ProjectResource', 'project',
                                 readonly=True)
    
    class Meta:
        queryset = Room.objects.all()
        resource_name = 'room'
        always_return_data = True
        authorization = DjangoAuthorization()
        
    def hydrate(self, bundle):
        """
        Set the attributes of the resource before it is saved to the database
        """
        
        bundle.obj.project = Project.objects.get(pk=bundle.data['project']['id'])
        
        return bundle
        
    def xdehydrate(self, bundle):
        """
        Prepare the data to be returned to the user
        """
        project = bundle.obj.project
        bundle.data['project'] = {'id': project.id,
                                  'codename': project.codename}
                                  
        return bundle
        