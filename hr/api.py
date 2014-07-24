"""
API file for hr
"""
import uuid
import logging

from django.db.models import Q
from django.utils.translation import activate
from tastypie.authorization import Authorization
from tastypie.resources import ModelResource
from tastypie import fields

from hr.models import Employee
from hr.validation import EmployeeValidation


logger = logging.getLogger(__name__)


class EmployeeResource(ModelResource):
    
    class Meta:
        queryset = Employee.objects.all()
        resource_name = 'employee'
        always_return_data = True
        authorization = Authorization()
        validation = EmployeeValidation()