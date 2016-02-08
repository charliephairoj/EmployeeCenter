import logging
import json
import time
from dateutil import parser
import pytz
from threading import Thread
from time import sleep

from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from rest_framework import generics
from rest_framework import viewsets
from django.conf import settings

from hr.serializers import EmployeeSerializer, AttendanceSerializer, ShiftSerializer, PayrollSerializer
from utilities.http import save_upload
from auth.models import S3Object
from hr.models import Employee, Attendance, Timestamp, Shift


logger = logging.getLogger(__name__)


def upload_attendance(request):
    if request.method == "POST":
        print 'ok'
        file = request.FILES.get('file')
        
        with open('attendance.txt', 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        lines = open('attendance.txt').readlines()
        data = [l.replace('\r\n', '').split('\t') for l in lines][:1000]
        print 'got lines'
        timestamps = []
        timezone = pytz.timezone('Asia/Bangkok')
        print "{0} lines long".format(len(data))
        
        def create_timestamps(data):
            print "Processing {0} timestamps".format(len(data))
            for index, d in enumerate(data):
            
                timestamp = timezone.localize(parser.parse(d[-1]))
           
                card_id = d[2]
                try:
                    employee = Employee.objects.get(Q(name__icontains=d[3]) | Q(card_id=d[2]))
                    employee.shift = Shift.objects.all()[0]
                    employee.save()
                except Employee.DoesNotExist:
                    employee = Employee.objects.create(name=d[3], card_id=int(d[2]), shift=Shift.objects.all()[0])
                    logger.warn("Employee {0} not found. Creating new employee".format(d[3]))
                
                try:
                    timestamps.append(Timestamp.objects.get(employee=employee, datetime=timestamp))
                except Timestamp.DoesNotExist:
                    timestamps.append(Timestamp.objects.create(employee=employee,
                                                                 datetime=timestamp))
                except Timestamp.MultipleObjectsReturned:
                    Timestamp.objects.filter(employee=employee, datetime=timestamp).delete()
                    timestamps.append(Timestamp.objects.create(employee=employee,
                                                                 datetime=timestamp))
                                                                 
        
        thread1 = Thread(target=create_timestamps, args=(data[1:len(data)/2], ))
        thread2 = Thread(target=create_timestamps, args=(data[len(data)/2:], ))
        
        threads = [thread1, thread2]
        
        thread1.start()
        thread2.start()
        
        while len([t for t in threads if t.isAlive()]) > 0:
            sleep(1)

        
        logger.warn("Clearing all old attendances. Only during development phase")
        Attendance.objects.all().delete()
        
        for t in timestamps:
            if Attendance.objects.filter(employee=t.employee, date=t.datetime.date()).count() == 0:
                attendance = Attendance.objects.create(employee=t.employee, date=t.datetime.date(), 
                                                       shift=t.employee.shift, pay_rate  =t.employee.wage)

                if t.time.hour < t.employee.shift.start_time.hour + 4:
                    attendance.start_time = t.time
                else:
                    attendance.end_time = t.time
            else:
                attendance = Attendance.objects.get(employee=t.employee, date=t.datetime.date())
                if t.time.hour < t.employee.shift.start_time.hour + 4:
                    attendance.start_time = t.time
                else:
                    attendance.end_time = t.time
            
            attendance.calculate_times()        
            attendance.save()
            
            
        response = HttpResponse(json.dumps({'status': 'ok'}),
                                content_type="application/json")
        response.status_code = 201
        return response
            
        
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
    
    def post(self, request, *args, **kwargs):
        request = self._format_primary_key_data(request)
        response = super(EmployeeList, self).post(request, *args, **kwargs)
        
        return response
        
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset.all()
        
        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(id__icontains=query) |
                                       Q(first_name__icontains=query) |
                                       Q(last_name__icontains=query) |
                                       Q(nickname__icontains=query) |
                                       Q(department__icontains=query) |
                                       Q(telephone__icontains=query))
                                       
        status = self.request.query_param.get('status', None)
        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        
        if status:
            query.filter(status__icontains=status)
            
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
        else:
            queryset = queryset[0:50]
            
        
        return queryset
    
    
class EmployeeDetail(EmployeeMixin, generics.RetrieveUpdateDestroyAPIView):
    def put(self, request, *args, **kwargs):
        request = self._format_primary_key_data(request)
        response = super(EmployeeDetail, self).put(request, *args, **kwargs)
        
        return response
    
    
class AttendanceMixin(object):
    queryset = Attendance.objects.all().order_by('-id')
    serializer_class = AttendanceSerializer
    
    
class AttendanceList(AttendanceMixin, generics.ListCreateAPIView):
    
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset
        
        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        employee_id = self.request.query_params.get('employee_id', None)
        
        # Search only attendances for selected employee
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        
        # Filter all records after the start_date
        if start_date:
            start_date = parser.parse(start_date)
            queryset = queryset.filter(date__gte=start_date)
            
        # Filter all records before end_date
        if end_date:
            end_date = parser.parse(end_date)
            queryset = queryset.filter(date__lte=end_date)
            
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
        else:
            queryset = queryset[0:50]
            
        
              
        return queryset
    
    
class AttendanceDetail(AttendanceMixin, generics.RetrieveUpdateDestroyAPIView):
    pass
    
    
class ShiftViewSet(viewsets.ModelViewSet):
    """
    API endpoint to view and edit configurations
    """
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    
    
class PayrollList(generics.ListCreateAPIView):
    queryset = Payroll.objects.all().order_by('-id')
    serializer_class = PayrollSerializer
    