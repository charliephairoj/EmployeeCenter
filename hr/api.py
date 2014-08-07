"""
API file for contacts
"""
import uuid
import logging

from django.db.models import Q
from django.utils.translation import activate
from tastypie.authorization import Authorization, DjangoAuthorization
from tastypie.resources import ModelResource
from tastypie import fields
from tastypie.constants import ALL, ALL_WITH_RELATIONS

from hr.models import Employee, Attendance


logger = logging.getLogger(__name__)


class EmployeeResource(ModelResource):
    
    class Meta:
        queryset = Employee.objects.all()
        resource_name = 'employee'
        always_return_data = True
        authorization = DjangoAuthorization()
        filtering = {
            'id': ALL,
            'name': ALL
        }

    def apply_filters(self, request, applicable_filters):
        obj_list = super(EmployeeResource, self).apply_filters(request, applicable_filters)
        
        if request.GET.has_key('q'):
            query = request.GET.get('q')
            obj_list = obj_list.filter(Q(name__icontains=query) | 
                                       Q(id__icontains=query))

        return obj_list
        
                                       
class AttendanceResource(ModelResource):
    employee = fields.ForeignKey('hr.api.EmployeeResource', 'employee')
    
    class Meta:
        queryset = Attendance.objects.all().order_by('-date')
        resource_name = 'attendance'
        always_return_data = True
        authorization = DjangoAuthorization()
        filtering = {
            'employee': ALL_WITH_RELATIONS,
            'date': ALL
        },
        excludes = ['_start_time', '_end_time']
        
    def dehydrate(self, bundle):
        """
        Dehydrate custom 
        """
        
        bundle.data.update({'start_time': bundle.obj.start_time,
                            'end_time': bundle.obj.end_time})
        return bundle
        