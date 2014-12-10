import logging

from rest_framework import serializers

from hr.models import Employee, Attendance


logger = logging.getLogger(__name__)


class EmployeeSerializer(serializers.ModelSerializer):
    social_security_id = serializers.CharField(required=False, allow_null=True)
    telephone = serializers.CharField(required=False, allow_null=True)
    
    class Meta:
        model = Employee
        exclude = ('shift', )
        

class AttendanceSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Attendance
        exclude = ('shift', )
        
        