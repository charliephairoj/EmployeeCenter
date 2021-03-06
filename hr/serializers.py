import logging
from dateutil import parser
from decimal import Decimal

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from pytz import timezone

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
    date = serializers.DateField(required=True)
    start_time = serializers.DateTimeField(required=False, allow_null=True)
    end_time = serializers.DateTimeField(required=False, allow_null=True)
    
    class Meta:
        model = Attendance
        read_only_fields = ('gross_wage', 'net_wage', 'lunch_pay', 'remarks')
        exclude = ('_start_time', '_end_time', '_enable_overtime')
        validators = [
            UniqueTogetherValidator(
                queryset=Attendance.objects.all(),
                fields=('date', 'employee')
            )
        ]
        
    def create(self, validated_data):
        """Create a new instance of Attendance
        """
        start_time = validated_data.pop('start_time', None)
        end_time = validated_data.pop('end_time', None)
        logger.debug(validated_data)
        instance = self.Meta.model.objects.create(**validated_data)

        instance.start_time = start_time
        instance.end_time = end_time
        instance.calculate_times()
        instance.save()
        
        return instance
        
    def update(self, instance, validated_data):
        
        enable_overtime = validated_data.pop('enable_overtime')
        instance.enable_overtime = enable_overtime
        instance.receive_lunch_overtime = validated_data.pop('receive_lunch_overtime', False)
        instance.vacation = validated_data.pop('vacation', False)
        instance.vacation_excused = validated_data.pop('vacation_excused', False)
        instance.sick_leave = validated_data.pop('sick_leave', False)
        instance.sick_leave_excused = validated_data.pop('sick_leave_excused', False)
        instance.cambodia = validated_data.pop('cambodia', False)
        instance.overtime_request = validated_data.pop('overtime_request', instance.overtime_request)
        instance.calculate_times()
        instance.save()
        
        return instance
        
    def to_representation(self, instance):

        ret = super(AttendanceSerializer, self).to_representation(instance)
        
        ret['start_time'] = instance.start_time
        ret['end_time'] = instance.end_time
        ret['enable_overtime'] = instance.enable_overtime

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
    #attendances = AttendanceSerializer(many=True, required=False, read_only=True)
    incentive_pay = serializers.DecimalField(required=False, decimal_places=2, max_digits=15, allow_null=True)
    shift = ShiftSerializer(required=False)
    card_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    employment_date = serializers.DateField(required=False, allow_null=True)
    
    class Meta:
        model = Employee
        fields = ('id', 'name', 'first_name', 'last_name', 'nationality', 'wage', 'department', 'shift',
                  'pay_period', 'image', 'telephone', 'nickname', 'social_security_id', 'government_id', 'card_id',
                  'bank', 'account_number', 'company', 'incentive_pay', 'status', 'payment_option', 'manager_stipend', 'title',
                  'location', 'employment_date')
    
    @staticmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        # select_related for "to-one" relationships
        queryset = queryset.select_related('image', 'shift')

        # prefetch_related for "to-many" relationships
        queryset = queryset.prefetch_related(
            'image',
            'shift',
            'equipments')

        # Prefetch for subsets of relationships
        queryset = queryset.prefetch_related(
            Prefetch('unaffiliated_attendees', 
                queryset=Attendee.objects.filter(organization__isnull=True))
            )
        return queryset

    def create(self, validated_data):
        """Create a new instance of Employee
        """
        shift = validated_data.pop('shift', None)
        if shift:
            shift = Shift.objects.get(pk=shift['id'])
        
        try:
            ed = timezone('Asia/Bangkok').normalize(validated_data.pop('employment_date'))
        except (AttributeError, KeyError) as e:
            ed = None
            logger.warn(e)

        instance = self.Meta.model.objects.create(shift=shift,
                                                  employment_date=ed,
                                                  **validated_data)
        
        return instance
        
    def update(self, instance, validated_data):
        
        shift_data = validated_data.pop('shift')
        try:
            ed = timezone('Asia/Bangkok').normalize(validated_data.pop('employment_date'))
        except (AttributeError, KeyError) as e:
            ed = None
            logger.info(e)

        instance.employment_date = ed
        instance.name = validated_data.pop('name', instance.name)
        instance.title = validated_data.pop('title', instance.title) 
        instance.shift = Shift.objects.get(start_time=shift_data['start_time'], end_time=shift_data['end_time'])
        instance.pay_period = validated_data.pop('pay_period', instance.pay_period)
        instance.nationality = validated_data.pop('nationality', instance.nationality)
        instance.telephone = validated_data.pop('telephone', instance.telephone)
        instance.department = validated_data.pop('department', instance.department)
        instance.card_id = validated_data.pop('card_id', instance.card_id)
        instance.bank = validated_data.pop('bank', instance.bank)
        instance.account_number = validated_data.pop('account_number', instance.account_number)
        instance.government_id = validated_data.pop('government_id', instance.government_id)
        instance.social_security_id = validated_data.pop('social_security_id', instance.social_security_id)
        instance.company = validated_data.pop('company', instance.company)
        instance.location = validated_data.pop('location', instance.location)
        instance.status = validated_data.pop('status', instance.status)
        
        instance.payment_option = validated_data.pop('payment_option', instance.payment_option)
        instance.wage = validated_data.pop('wage', 0)
        instance.manager_stipend = validated_data.pop('manager_stipend', 0) 
        instance.incentive_pay = validated_data.pop('incentive_pay', 0) 
        
        instance.image = validated_data.pop('image', instance.image)
    
        instance.save()
        
        return instance
        
    def to_representation(self, instance):
        """
        Override the 'to_representation' method to allow integration of products into 
        output data
        """
        ret = super(EmployeeSerializer, self).to_representation(instance)
        
        try:
            iam_credentials = self.context['request'].user.aws_credentials
            key = iam_credentials.access_key_id
            secret = iam_credentials.secret_access_key
        except AttributeError as e:
            pass

        try:
            ret['image'] = {'id': instance.image.id,
                            'url': instance.image.generate_url()}
        except AttributeError: 
            pass
            
        request = self.context['request']
        
        start_date = request.query_params.get('start_date', None)
        end_date =  request.query_params.get('end_date', None) 
        
        
        if start_date and end_date:
            start_date = parser.parse(start_date)
            end_date = parser.parse(end_date)
            attendances = instance.attendances.filter(date__gte=start_date,
                                                      date__lte=end_date)
            
            regular_time = 0
            overtime = 0                               
            gross_wage = 0
            net_wage = 0
            reimbursements = 0
            incentive_pay = 0
            sunday_time = 0
            sunday_overtime = 0
            
            for a in attendances:
                                
                if a.start_time and a.end_time:
                    a.calculate_net_wage()
                    if a.is_sunday:
                        sunday_time += a.regular_time
                        sunday_overtime += a.overtime
                    else:
                        regular_time += a.regular_time
                        overtime += a.overtime
                    gross_wage += a.gross_wage
                    reimbursements += a.reimbursement
                    incentive_pay += a.incentive_pay
                    net_wage += a.net_wage
                    
            if instance.pay_period == 'monthly':
                gross_wage = instance.wage / Decimal('2')
                net_wage = gross_wage + reimbursements + incentive_pay
                
            if start_date.day > 10 and start_date.day < 26:
                net_wage += instance.manager_stipend
                
            ret['regular_time'] = regular_time / Decimal('8')
            ret['overtime'] = overtime
            ret['sunday_time'] = sunday_time / Decimal('8')
            ret['sunday_overtime'] = sunday_overtime / Decimal('8')
            ret['gross_wage'] = gross_wage
            ret['reimbursements']  =reimbursements
            ret['total_incentive_pay'] = incentive_pay
            ret['net_wage'] = net_wage
            
        ret['equipments'] = [{'brand': e.brand,
                              'description': e.description} for e in instance.equipments.all()]
         
        return ret


class EmployeeFieldSerializer(serializers.ModelSerializer):

    class Meta:
        model = Employee
        fields = ('id', 'name', 'first_name', 'last_name', 'nationality', 'department', 'company', 'card_id')

        
class PayrollSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Payroll
        fields = ('start_date', 'end_date')
        
    def create(self, validated_data):
        
        start_date = validated_data.pop('start_date')
        end_date = validated_data.pop('end_date')
        
        instance = Payroll.objects.create(start_date, end_date)
        
        return instance
    
    
    
    
    
    
        