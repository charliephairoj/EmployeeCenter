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

from projects.models import Project


logger = logging.getLogger(__name__)


class ProjectResource(ModelResource):
    
    class Meta:
        queryset = Project.objects.all()
        resource_name = 'project'
        always_return_data = True
        authorization = DjangoAuthorization()
        
    