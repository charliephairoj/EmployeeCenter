import logging

from rest_framework import generics
from hr.serializers import EmployeeSerializer, AttendanceSerializer
from django.conf import settings

from hr.models import Employee, Attendance


logger = logging.getLogger(__name__)


def employee_image(request):
    if request.method == "POST":
        filename = save_upload(request)
        obj = S3Object.create(filename,
                        "employee/image/{0}.jpg".format(time.time()),
                        'media.dellarobbiathailand.com')
        response = HttpResponse(json.dumps({'id': obj.id,
                                            'url': obj.generate_url()}),
                                content_type="application/json")
        response.status_code = 201
        return response
        
class EmployeeMixin(object):
    queryset = Employee.objects.all().order_by('name')
    serializer_class = EmployeeSerializer
    
    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        fields = ['image']
        
        for field in fields:
            if field in request.data:
                try:
                    if 'id' in request.data[field]:
                        request.data[field] = request.data[field]['id']
                except TypeError:
                    pass
                                    
        return request
    
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