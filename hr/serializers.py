import logging

from rest_framework import serializers

from hr.models import Employee, Attendance, Shift, PayRecord, Payroll
from media.models import S3Object


logger = logging.getLogger(__name__)


class ShiftSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=True)
    
    class Meta:
        model = Shift
        fields = ('id', 'start_time', 'end_time')
        

class AttendanceSerializer(serializers.ModelSerializer):
    enable_overtime = serializers.BooleanField(default=False, write_only=True)
    date = serializers.DateField(read_only=True)
        
    class Meta:
        model = Attendance
        exclude = ('_start_time', '_end_time', '_enable_overtime')
        
    def update(self, instance, validated_data):
        
        enable_overtime = validated_data.pop('enable_overtime')
        logger.warn(enable_overtime)
        instance.enable_overtime = enable_overtime
        logger.warn(instance.enable_overtime)
        instance.calculate_times()
        
        return instance
        
    def to_representation(self, instance):

        ret = super(AttendanceSerializer, self).to_representation(instance)
        
        ret['start_time'] = instance.start_time
        ret['end_time'] = instance.end_time
        ret['enable_overtime'] = instance.enable_overtime
        logger.warn(ret)
        return ret
        

class EmployeeSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    nickname = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    nationality = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    department = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    company = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    social_security_id = serializers.CharField(required=False, 
                                               allow_null=True,
                                               allow_blank=True)
    telephone = serializers.CharField(required=False, 
                                      allow_null=True,
                                      allow_blank=True)
    image = serializers.PrimaryKeyRelatedField(queryset=S3Object.objects.all(),
                                               required=False, 
                                               allow_null=True)
    wage = serializers.DecimalField(required=False, decimal_places=2, max_digits=12, allow_null=True)
    pay_period = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    attendances = AttendanceSerializer(many=True, required=False, read_only=True)
    shift = ShiftSerializer(required=False)
    
    
    class Meta:
        model = Employee
        fields = ('id', 'name', 'first_name', 'last_name', 'nationality', 'wage', 'department', 'shift',
                  'pay_period', 'image', 'telephone', 'nickname', 'social_security_id', 'attendances', 'government_id', 'card_id',
                  'bank', 'account_number', 'company', 'incentive_pay', 'status', 'payment_option')
    
    def update(self, instance, validated_data):
        
        shift_data = validated_data.pop('shift')
        
        instance.shift = Shift.objects.get(start_time=shift_data['start_time'], end_time=shift_data['end_time'])
        instance.pay_period = validated_data.pop('pay_period', instance.pay_period)
        instance.nationality = validated_data.pop('nationality', instance.nationality)
        instance.department = validated_data.pop('department', instance.department)
        instance.card_id = validated_data.pop('card_id', instance.card_id)
        instance.bank = validated_data.pop('bank', instance.bank)
        instance.account_number = validated_data.pop('account_number', instance.account_number)
        instance.government_id = validated_data.pop('government_id', instance.government_id)
        instance.social_security_id = validated_data.pop('social_security_id', instance.social_security_id)
        instance.company = validated_data.pop('company', instance.company)
        
        instance.wage = validated_data.pop('wage', 0)
        
        instance.save()
        
        return instance
        
    def to_representation(self, instance):
        """
        Override the 'to_representation' method to allow integration of products into 
        output data
        """
        ret = super(EmployeeSerializer, self).to_representation(instance)
        
        iam_credentials = self.context['request'].user.aws_credentials
        key = iam_credentials.access_key_id
        secret = iam_credentials.secret_access_key
        
        try:
            ret['image'] = {'id': instance.image.id,
                            'url': instance.image.generate_url(key, secret)}
        except AttributeError: 
            pass
            
        return ret
        
        
class PayrollSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Payroll
        
    def create(self, validated_data):
    
    
    
    
    
    
    
        