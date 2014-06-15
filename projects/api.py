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

from projects.models import Project, ProjectSupply
from supplies.models import Supply


logger = logging.getLogger(__name__)


class ProjectResource(ModelResource):
    
    customer = customer = fields.ToOneField('contacts.api.CustomerResource', 'customer', null=True,
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
    
    def dehydrate(self, bundle):
        """
        Custom Dehydration for the project resource
        """
        #Dehydrate the supply
        bundle.data['supplies'] = [{'id': ps.id,
                                    'description': ps.supply.description} for ps in ProjectSupply.objects.filter(project=bundle.obj)]
        return bundle
        
    def add_supply(self, request, **kwargs):
        """
        Adds a new supply to the project
        """
        if reequest.method = "POST":
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
        
        
        
        
        