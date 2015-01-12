import logging

from rest_framework import serializers

from hr.models import Employee, Attendance
from media.models import S3Object

logger = logging.getLogger(__name__)


class EmployeeSerializer(serializers.ModelSerializer):
    nickname = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    social_security_id = serializers.CharField(required=False, 
                                               allow_null=True)
    telephone = serializers.CharField(required=False, 
                                      allow_null=True)
    image = serializers.PrimaryKeyRelatedField(queryset=S3Object.objects.all(),
                                               required=False, 
                                               allow_null=True)
    wage = serializers.DecimalField(required=False, decimal_places=2, max_digits=12, allow_null=True)
    pay_period = serializers.CharField(required=False, allow_null=True)
    
    
    class Meta:
        model = Employee
        fields = ('id', 'name', 'wage', 'pay_period', 'image', 'telephone', 'nickname', 'social_security_id')
        
    def to_representation(self, instance):
        """
        Override the 'to_representation' method to allow integration of products into 
        output data
        """
        ret = super(EmployeeSerializer, self).to_representation(instance)

        try:
            ret['image'] = {'id': instance.image.id,
                            'url': instance.image.generate_url()}
        except AttributeError: 
            pass
            
        return ret
        
class AttendanceSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Attendance
        exclude = ('shift', )
        
        