import logging

from rest_framework import generics
from hr.serializers import EmployeeSerializer, AttendanceSerializer

from hr.models import Employee, Attendance


logger = logging.getLogger(__name__)


class EmployeeMixin(object):
    queryset = Employee.objects.all().order_by('name')
    serializer_class = EmployeeSerializer
    
    
class EmployeeList(EmployeeMixin, generics.ListCreateAPIView):
    
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset
        
        #Filter based on query
        query = self.request.QUERY_PARAMS.get('q', None)
        if query:
            queryset = queryset.filter(Q(name__icontains=query) |
                                       Q(department__icontains=query) |
                                       Q(telephone__icontains=query))
                  
        return queryset
    
    
class EmployeeDetail(EmployeeMixin, generics.RetrieveUpdateDestroyAPIView):
    pass
    
    
class AttendanceMixin(object):
    queryset = Attendance.objects.all().order_by('id')
    serializer_class = AttendanceSerializer
    
    
class AttendanceList(AttendanceMixin, generics.ListCreateAPIView):
    
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset
        
        """
        #Filter based on query
        query = self.request.QUERY_PARAMS.get('q', None)
        if query:
            queryset = queryset.filter(Q(name__icontains=query) |
                                       Q(email__icontains=query) |
                                       Q(telephone__icontains=query) |
                                       Q(notes__icontains=query))
        """
        
        employee_id = self.request.query_params.get('employee_id', None)
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
              
        return queryset
    
    
class AttendanceDetail(AttendanceMixin, generics.RetrieveUpdateDestroyAPIView):
    pass