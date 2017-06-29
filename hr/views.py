import logging
import json
from dateutil import parser
import pytz
from threading import Thread
from time import sleep
from datetime import time, datetime

import boto
from django.template.loader import render_to_string
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from rest_framework import generics
from rest_framework import viewsets
from django.conf import settings

from hr.serializers import EmployeeSerializer, AttendanceSerializer, ShiftSerializer, PayrollSerializer
from utilities.http import save_upload
from auth.models import S3Object
from hr.models import Employee, Attendance, Timestamp, Shift, Payroll


logger = logging.getLogger(__name__)


def upload_attendance(request):
    if request.method == "POST":
        file = request.FILES.get('file')
        
        with open('attendance.txt', 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        lines = open('attendance.txt').readlines()
        data = [l.replace('\r\n', '').split('\t') for l in lines]

        timestamps = []
        error_times = []
        employees = {}
        missing_employees = {}
        duplicate_employees = []
        timezone = pytz.timezone('Asia/Bangkok')

        def create_timestamps(data):

            for index, d in enumerate(data):
                employee = None
                timestamp = timezone.localize(parser.parse(d[-1]))
                card_id = d[2]
                
                # Find the employee with the corresponding card
                try:
                    if card_id in employees:
                        employee = employees[card_id]
                    else:
                        employee = Employee.objects.get(card_id=card_id)
                        employee.shift = Shift.objects.all()[0]
                        employee.save()
                        employees[employee.card_id] = employee

                except Employee.DoesNotExist:
                    missing_employees[card_id] = {'id': d[2], 'timestamp': timestamp, 'card_id': card_id}
                    #logger.warn('No employee for card ID {0} on date: {1}'.format(card_id, timestamp))
                except Employee.MultipleObjectsReturned as e:
                    duplicate_employees.append({'id': d[2], 'timestamp': timestamp})
                    #logger.warn(e)
                
                if employee:
                    try:
                        timestamps.append(Timestamp.objects.get(employee=employee, datetime=timestamp))
                    except Timestamp.DoesNotExist:
                        timestamps.append(Timestamp.objects.create(employee=employee,
                                                                     datetime=timestamp))
                    except Timestamp.MultipleObjectsReturned:
                        Timestamp.objects.filter(employee=employee, datetime=timestamp).delete()
                        timestamps.append(Timestamp.objects.create(employee=employee,
                                                                     datetime=timestamp))
                                                                 
            
        def create_attendances(timestamps):
            for t in timestamps:
                count = Attendance.objects.filter(employee=t.employee, date=t.datetime.date()).count()
                if count == 0:
                    attendance = Attendance.objects.create(employee=t.employee, date=t.datetime.date(), 
                                                           shift=t.employee.shift, pay_rate=t.employee.wage)
                elif count == 1:
                    attendance = Attendance.objects.get(employee=t.employee, date=t.datetime.date())
                elif count > 1:
                    Attendance.objects.filter(employee=t.employee, date=t.datetime.date()).delete()
                    attendance = Attendance.objects.create(employee=t.employee, date=t.datetime.date(), 
                                                           shift=t.employee.shift, pay_rate=t.employee.wage)
                    
            
                if t.time.hour < t.employee.shift.start_time.hour + 4:
                    attendance.start_time = t.time
                else:
                    attendance.end_time = t.time
                attendance.save()
                
                assert attendance.id is not None
                assert attendance.date is not None
                #logger.debug("{0}: {1} | {2}".format(attendance.date, attendance.employee.id, attendance.id))
        
            
        def create_timestamps_and_attendances(data):
            thread1 = Thread(target=create_timestamps, args=(data[1:len(data)/2], ))
            thread2 = Thread(target=create_timestamps, args=(data[len(data)/2:], ))
        
            threads = [thread1, thread2]
        
            thread1.start()
            thread2.start()
        
            while len([t for t in threads if t.isAlive()]) > 0:
                sleep(100)
                
            create_attendances(timestamps)
            
            logger.debug("Emailing Attenance Upload Report")
            
            heading = """Attendance Upload Report"""
            header_cell_style = """
                                border-right:1px solid #595959;
                                border-bottom:1px solid #595959;
                                border-top:1px solid #595959;
                                padding:1em;
                                text-align:center;
                                """
            message = render_to_string("attendance_upload_email.html", 
                                       {'heading': heading,
                                        'header_style': header_cell_style,
                                        'missing_employees': missing_employees,
                                        'duplicate_employees': duplicate_employees})
    
            e_conn = boto.ses.connect_to_region('us-east-1')
            e_conn.send_email('noreply@dellarobbiathailand.com',
                              'Attendance Upload Report',
                              message,
                              ["charliep@dellarobbiathailand.com"],
                              format='html')
            
            
            
        # Primary parallel thread
        primary_thread = Thread(target=create_timestamps_and_attendances, args=(data[0:50], ))
        primary_thread.start()
        
                
        response = HttpResponse(json.dumps({'status': 'We will send you an email once the upload has completed.'}),
                                content_type="application/json")
        response.status_code = 201
        return response
            
        
def employee_image(request):
    if request.method == "POST":
        filename = save_upload(request)
        obj = S3Object.create(filename,
                        "employee/image/{0}.jpg".format(datetime.now().microsecond),
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
        queryset = self.queryset.all().order_by('status', 'government_id', 'card_id', 'name')
        
        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(id__icontains=query) |
                                       Q(first_name__icontains=query) |
                                       Q(last_name__icontains=query) |
                                       Q(card_id__icontains=query) |
                                       Q(name__icontains=query) |
                                       Q(nickname__icontains=query) |
                                       Q(department__icontains=query) |
                                       Q(telephone__icontains=query))
                                       
        status = self.request.query_params.get('employee_status', None)
        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
                
        if status:
            queryset = queryset.filter(status=status)
            
        if offset != None and limit == 0:
            queryset = queryset[offset:]
        elif offset == 0 and limit != 0:
            queryset = queryset[offset:offset + limit]
        else:
            queryset = queryset[offset: offset + settings.REST_FRAMEWORK['PAGINATE_BY']]
        
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
    
    
    def post(self, request, *args, **kwargs):
        
        tz = pytz.timezone('Asia/Bangkok')
        
        a_date = parser.parse(request.data['date']).astimezone(tz).date()
        request.data['date'] = a_date
        
        s_time = parser.parse(request.data['start_time'])
        s_time = s_time.astimezone(tz)
        s_time = datetime.combine(a_date, s_time.timetz())
        request.data['start_time'] = s_time
        
        e_time = parser.parse(request.data['end_time'])
        e_time = e_time.astimezone(tz)
        e_time = datetime.combine(a_date, e_time.timetz())
        request.data['end_time'] = e_time
        
        try:
            o_time = parser.parse(request.data['overtime_request'])
            o_time = tz.localize(o_time)
            o_time = datetime.combine(a_date, o_time.timetz())
            request.data['overtime_request'] = o_time
        except KeyError as e:
            logger.warn(e)
        
        response = super(AttendanceList, self).post(request, *args, **kwargs)
        
        return response
            
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset.order_by()
        
        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        employee_id = self.request.query_params.get('employee_id', None)
        
        if employee_id or start_date or end_date:
            query = "SELECT * FROM hr_attendances WHERE "
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
    
        if offset:
            queryset = queryset[offset - 1:]
        else:
            queryset = queryset[0:]
                          
        return queryset
    
    
class AttendanceDetail(AttendanceMixin, generics.RetrieveUpdateDestroyAPIView):
    
    def put(self, request, *args, **kwargs):
        
        tz = pytz.timezone('Asia/Bangkok')
        
        a_date = parser.parse(request.data['date']).astimezone(tz).date()
        request.data['date'] = a_date
        
        try:
            s_time = parser.parse(request.data['start_time'])
            s_time = s_time.astimezone(tz)
            s_time = datetime.combine(a_date, s_time.timetz())
            request.data['start_time'] = s_time
        except AttributeError as e:
            pass
        
        try:
            e_time = parser.parse(request.data['end_time'])
            e_time = e_time.astimezone(tz)
            e_time = datetime.combine(a_date, e_time.timetz())
            request.data['end_time'] = e_time
        except AttributeError as e:
            pass
        
        try:
            o_time = parser.parse(request.data['overtime_request'])
            o_time = o_time.astimezone(tz)
            o_time = datetime.combine(a_date, o_time.timetz())
            request.data['overtime_request'] = o_time
        except KeyError as e:
            logger.warn(e)
        
        response = super(AttendanceDetail, self).put(request, *args, **kwargs)
        
        return response
    
    
class ShiftViewSet(viewsets.ModelViewSet):
    """
    API endpoint to view and edit configurations
    """
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    
    
class PayrollList(generics.ListCreateAPIView):
    queryset = Payroll.objects.all().order_by('-id')
    serializer_class = PayrollSerializer
    