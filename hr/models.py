"""
Models to be use in the HR application
"""
import logging
from decimal import Decimal
from datetime import date, datetime, timedelta
import math
from math import floor
import traceback

from django.db import models
from pytz import timezone

from media.models import S3Object


logger = logging.getLogger(__name__)
            
          
class Shift(models.Model):
    
    start_time = models.TimeField(db_column="start_time")
    end_time = models.TimeField(db_column="end_time")  
    
    
class Employee(models.Model):
    
    name = models.TextField(db_column="name", null=True)
    first_name = models.TextField(null=True, blank=True)
    last_name = models.TextField(default="", null=True, blank=True)
    nickname = models.TextField(null=True, default="")
    nationality = models.TextField(default="")
    legal = models.BooleanField(default=True)
    department = models.TextField()
    telephone = models.TextField(null=True)
    wage = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    pay_period = models.TextField(default="daily")
    employement_date = models.DateField(null=True)
    social_security_id = models.TextField(null=True)
    shift = models.ForeignKey(Shift, null=True)
    image = models.ForeignKey(S3Object, null=True, blank=True)
    last_modified = models.DateTimeField(auto_now=True)
    card_id = models.TextField(null=True)
    bank = models.TextField(blank=True, null=True)
    account_number = models.TextField(null=True, blank=True)
    government_id = models.TextField(null=True, blank=True)
    company = models.TextField(null=True)
    incentive_pay = models.DecimalField(decimal_places=2, max_digits=12, default=0) #new 
    status = models.TextField(default='active') #new
    payment_option = models.TextField(null=True) #new
    
    class Meta:
        permissions = (('can_view_pay_rate', 'Can view pay rate'),)
                       
    @property
    def xname(self):
        try:
            return "{0} {1}".format(self.first_name, self.last_name or "")
        except Exception:
            return ""


class Timestamp(models.Model):
    datetime = models.DateTimeField()
    employee = models.ForeignKey(Employee, related_name='timestamps')
    tz = timezone('Asia/Bangkok')
    
    @property
    def time(self):
        try:
            return self.datetime.astimezone(self.tz)
        except AttributeError as e:
            logger.warn(e)
            return None
    
    
class Attendance(models.Model):
    
    date = models.DateField(db_column='a_date')
    _start_time = models.DateTimeField(null=True, db_column='start_time')
    _end_time = models.DateTimeField(null=True, db_column='end_time')
    employee = models.ForeignKey(Employee, related_name='attendances')
    _enable_overtime = models.BooleanField(default=False, db_column="enable_overtime")
    regular_time = models.DecimalField(decimal_places=2, max_digits=12, null=True)
    overtime = models.DecimalField(decimal_places=2, max_digits=12, default=0, null=True)
    doubletime = models.DecimalField(decimal_places=2, max_digits=12, default=0, null=True)
    total_time = models.DecimalField(decimal_places=2, max_digits=12, null=True)
    shift = models.ForeignKey(Shift, null=True)
    salaried = models.BooleanField(default=False) #new
    receive_lunch_overtime = models.BooleanField(default=False) #new
    pay_rate = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    regular_pay = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    overtime_pay = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    lunch_pay = models.DecimalField(decimal_places=2, max_digits=12, default=0) #new
    
    # Wages
    gross_wage = models.DecimalField(decimal_places=2, max_digits=12, default=0) #new 
    net_wage = models.DecimalField(decimal_places=2, max_digits=12, default=0) #new
    
    #Reimbursements
    reimbursement = models.DecimalField(decimal_places=2, max_digits=12, default=0) #new
    incentive_pay = models.DecimalField(decimal_places=2, max_digits=12, default=0) #new 
    
    # Special days that affect the pay rate
    is_holiday = models.BooleanField(default=False) #new
    sick_leave = models.BooleanField(default=False) #new
    vacation = models.BooleanField(default=False) #new
    
    # Pay Rates for non regular days
    sunday_pay_rate = 2
    sunday_ot_pay_rate = 3
    holiday_pay_rate = 2.5
    holiday_ot_pay_rate = 2.5
    
    remarks = models.TextField(default='') #new

    
    @property
    def is_sunday(self):
        """Return True if day of the week is Sunday"""
        return True if self.date.weekday() == 6 else False

    @property
    def start_time(self):
        try:
            return self._start_time.astimezone(self.tz)
        except AttributeError:
            return None
        
    @start_time.setter
    def start_time(self, value):
        self._start_time = value
    
    @property
    def end_time(self):
        try:
            return self._end_time.astimezone(self.tz)
        except AttributeError as e:
            return None
        
    @end_time.setter
    def end_time(self, value):
        self._end_time = value

    
    @property
    def enable_overtime(self):
        """
        Getter for enable overtime
        """
        return self._enable_overtime
        
    @enable_overtime.setter
    def enable_overtime(self, value):
        self._enable_overtime = bool(value)
        
        
    def __init__(self, *args, **kwargs):
        """
        Override the initialization method
        """
        super(Attendance, self).__init__(*args, **kwargs)
        
        #Set standard timezone
        self.tz = timezone('Asia/Bangkok')
        
        # Set the pay rate if not set and not specified
        if 'pay_rate' not in kwargs and not self.pay_rate:
            self.pay_rate = self.employee.wage
        
        # Set the shift if not set and not specified
        if 'shift' not in kwargs and not self.shift:
            self.shift = self.employee.shift
            
        if self.start_time and self.end_time:
            self.calculate_times()
                            
    def calculate_times(self):
        """Calculate the different times based on the assigned shift
        
        This method will calculate the regular time, overtime, and lunch overtime based on the 
        assigned shift for this attendance. 
        
        - Calculate the regular time
        - Calculate the overtime
        - Calculate lunch overtime 
        """
        self.regular_time = self._calculate_regular_time()
        self.overtime = self._calculate_overtime()
        
    def calculate_gross_wage(self):
        """Calculate the gross wage for this attendance
        
        This method will calculate the gross wage for this attendance. The steps are:
        - 1. Determine not vacation or sick leave
        -   1.1 Calculate pay for regular time
        -   1.2 Calculate pay for overtime if enabled
        -   1.3 Calculate pay for lunch overtime
        """
        if not self.sick_leave and not self.vacation:
            
            # Calculate the regular wage if not a salaried employee
            if not self.salaried:
                self.regular_pay = self._calculate_regular_pay_rate()
            else: 
                self.regular_pay = 0

            # Calculate the overtime wage if overtime is enabled
            if self.enable_overtime:
                self.overtime_pay = self.overtime * self._calculate_overtime_pay_rate()
            else: 
                self.overtime_pay = 0
                
            # Calculate the overtime wage if this employee is to receive lunch overtime
            if self.receive_lunch_overtime:
                self.lunch_pay = (self.pay_rate / Decimal('8')) * Decimal('1.5')
            else:
                self.lunch_pay = 0
            
            gross_wage = self.regular_pay + self.overtime_pay + self.lunch_pay
        
        # If attendance is for vacation or sick leave pay only regular wage
        else:
            gross_wage = self.regular_pay
            
        self.gross_wage = gross_wage
        
        return self.gross_wage
       
    def calculate_net_wage(self):
        """Calculate the net wage for this attendance
        
        This method will calculate the net wage by accounting for reimbursements and deductions.
        
        - 1. Get the gross wage
        - 2. Calculate reimbursements
        -   2.1 Calculate lunch costs
        -   2.2 Calculate overtime meal if over 5 hours
        -   2.3 Calculate incentive pay
        - 3. Calculate deductions
        -   3.1 Calculate if late
        """
        self.remarks = ''
        
        gross_wage = self.calculate_gross_wage()
        
        # Calculate the reimbursements
        reimbursements = 0 
        
        # Calculate mid meal reimbursement
        if self.receive_lunch_overtime:
            reimbursements = Decimal('30')
            
            # Add a note for lunch reimbursement
            self.remarks += u'- Reimbursed 30THB for lunch \n'
            
        if self.overtime >= Decimal('5'):
            reimbursements += Decimal('30')
        
            # Add a note for overtime meal reimbursement
            self.remarks += u'- Reimbursed 30THB for working over 4 hours of overtime \n'
        
        if not self.vacation and not self.sick_leave and self.regular_time >= Decimal('8'):
            self.incentive_pay = self.employee.incentive_pay
            reimbursements += self.incentive_pay
            
            # Add a note incentive pay
            self.remarks += u'- Reimbursed {0}THB for incentive pay \n'.format(self.incentive_pay)
        
        
        self.reimbursement = reimbursements
        
        # Calculate deductions
        
        self.net_wage = gross_wage + reimbursements
            
        return self.net_wage        
        
    def _calculate_regular_time(self):
        """Calculate the regular time based on the assigned shift
        
        This method will calculate the regular, while looking at if the employee clocked
        in late, or left work early
        
        Rules:
        - Determine the start time for calculation based on if the employee clocked in
          late or not
        - Employees are giving a leeway of 10 minutes after shift starts
        - Determine the end time based on if the employee clocked out early.
        - End time cannot be greater than end of shift time
        """
        
        # Determine the proper start time by testings if the clockin time was late
        if self.start_time.time() >= (datetime.combine(self.date, self.shift.start_time) + timedelta(minutes=10)).time():
            start_time = self.start_time
        else:
            start_time = datetime.combine(self.date, self.shift.start_time).replace(tzinfo=self.tz)
            
        if self.end_time.time() < self.shift.end_time:
            end_time = self.end_time
        else:
            end_time = datetime.combine(self.date, self.shift.end_time).replace(tzinfo=self.tz)
                
        t_delta = self._calculate_timedelta(start_time, end_time)
        
        # Calculate total amount of regular time worked
        regular_time = (Decimal(str(t_delta.total_seconds())) / Decimal('3600')) - Decimal('1')
        
        return regular_time
        
    def _calculate_overtime(self):
        """Calculates the number of overtime hours due to the employee
        
        Rules:
        - Will only calculate overtime if it is enabled
        - Must work at least 1 hour past end of shift
        - Overtime granted by the hour
        """
        if self.enable_overtime:
            
            # Calculate the minium end time for overtime to actually take place
            minimum_end_time = datetime.combine(self.date, self.shift.end_time.replace(tzinfo=self.tz))
            minimum_end_time = self.tz.normalize(minimum_end_time)
            minimum_end_time += timedelta(hours=1)

            if self.end_time > minimum_end_time:
                
                t_delta = self._calculate_timedelta(self.shift.end_time, self.end_time)
                # Convert time delta to time decimal
                overtime = Decimal(str(t_delta.total_seconds())) / Decimal('3600')
                # Round down to the nearest hour
                truncated_overtime = Decimal(str(math.floor(overtime)))
                
                return truncated_overtime
        
        # Return 0 if any of the coniditions fail       
        return Decimal('0')
        
    def _calculate_regular_pay_rate(self):
        """Calculate the pay rate for employees during regular time
        """
        if self.is_sunday:
            return self.pay_rate * Decimal(str(self.sunday_pay_rate))
        elif self.is_holiday:
            return self.pay_rate * Decimal(str(self.holiday_pay_rate))
        else:
            return self.pay_rate
        
    def _calculate_overtime_pay_rate(self):
        """Calculate the hourly pay rate for overtime
        
        This method will calculate the hourly pay rate for overtime based on 
        the following steps
        
        - 1. Calculate hour regular pay rate
        - 2. Calculate sunday overtime pay rate
        - 3. Calculate holiday overtime pay rate
        - 4. Calculate regular overtime pay rate
        """
        if not self.salaried:
            hourly_rate = self.pay_rate / Decimal('8')
        else:
            hourly_rate = (self.pay_rate / Decimal('30')) / Decimal('8')
        
        if self.is_sunday:
            return hourly_rate * Decimal(str(self.sunday_ot_pay_rate))
        elif self.is_holiday:
            return hourly_rate * Decimal(str(self.holiday_ot_pay_rate))
        else:
            return hourly_rate * Decimal('1.5')
        
    def _calculate_timedelta(self, t1, t2):
        """Calculate the differences in two times
        """
        fmt = '%H:%M:%S'
        s1 = t1.strftime(fmt)
        s2 = t2.strftime(fmt)
        t_delta = datetime.strptime(s2, fmt) - datetime.strptime(s1, fmt)
        
        return t_delta


class PayrollManager(models.Model):
    
    def create(self, start_date, end_date, *args, **kwargs):
        
        payroll = Payroll(start_date=start_date,
                          end_date=end_date)
        payroll.save()
        
        for employee in Employee.objects.filter(status='active'):
            
            record = PayRecord.objects.create(employee,
                                              start_date=start_date,
                                              end_date=end_date,
                                              payroll=payroll)
                            
        
class Payroll(models.Model):
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False)
    
    objects = PayrollManager()
    
    def create(self, start_date, end_date):
        """Create a payroll for the specified pay period
        
        This method will calculate the total wages"""
    
    
class PayRecordManager(models.Manager):
    
    def create(self, employee, start_date, end_date, *args, **kwargs):
        """Create a new PayRecord for the given dates
        
        This method will calculate """
        record = PayRecord(employee=employee, start_date=start_date,
                           end_date=end_date)
        record.calculate_net_wage()
        record.save()
        
        return record
        
class PayRecord(models.Model):
    payroll = models.ForeignKey(Payroll, related_name='pay_records')
    employee = models.ForeignKey(Employee, related_name='pay_records')
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False)
    gross_wage = models.DecimalField(null=False)
    net_wage = models.DecimalField(null=False)
    reimbursements = models.DecimalField(default=0)
    deductions = models.DecimalField(null=False)
    social_security_withholding = models.DecimalField(null=False)
    tax_withholding = models.DecimalField(null=False)
    remarks = models.TextField(default='')
    
    objects = PayRecordManager()
    
    def calculate_gross_wage(self):
        """Calculate the total gross wage
        
        This method will loop through all the attendances and
        calculate the total gross wage
        """
        gross_wage = 0
        
        if self.employee.pay_period.lower() == 'monthly':
            self.gross_wage = self.employee.wage / Decimal('2')
        
        elif self.employee.pay_period.lower() == 'daily':
            attendances = self._get_employee_attendances()
            for attendance in attendances:
                gross_wage += attendance.gross_wage

            self.gross_wage = gross_wage

        return self.gross_wage
        
    def calculate_net_wage(self):
        """Calculate the total net wage
        
        This method will calculate the total net wage for the pay period through
        the following steps:
        
        - 1. Get gross wage
        - 2. Calculate all reimbursements
        - 3. Calculate all deductions
        -   3.1 Calculate social security withholding
        -   3.2 Calculate tax withholding
        """
        gross_pay = self.calculate_gross_wage()
        
        incentive_pay = 0
        reimbursements = 0
        deductions = 0
        regular_pay = 0
        
        # Loop through all the attendances 
        attendances = self._get_employee_attendances()
        for attendance in attendances:
            
            # Calculate regular pay for use in calculating
            # social security later
            regular_pay += attendance.regular_pay

            # Calculate all incentive pay
            incentive_pay += attendance.incentive_pay
            
            # Calculate reimbursements
            self.reimbursements += attendance.reimbursement
            self.remarks += "\n\n{0}:\n{1}".format(attendance.date, 
                                                attendance.remarks)

            # Calculate the deductions
            #deductions += attendance.deduction
            
        
        # Calculate social security
        if self.employee.pay_period.lower() == 'daily':
            ss_w = regular_pay * Decimal('0.05')
        elif self.employee.pay_period.lower() == 'monthly':
            ss_w = self.gross_wage * Decimal('0.05')
        self.social_security_withholding = ss_w

        net_wage = gross_pay
        net_wage += self.reimbursements
        net_wage -= self.social_security_withholding
        
        self.net_wage = net_wage
        
        return self.net_wage
    
    def add_reimbursement(self, amount, note):
        """Adds a reimbursement for the pay record
        
        This mother will add a reimbursement to the total reimbursement
        and add a note to the remarks"""
        self.reimbursements += amount
        
        self.remarks += '{0}\n'.format(note)
        
    def _get_employee_attendances(self):
        """Return all the attendances for this employee during
        this pay period.
        
        This method will filter all attendances for attendances that match
        the employee and the are within the date ranges
        """
        if not hasattr(self, 'queryset'):
            self.queryset = Attendance.objects.filter(employee=self.employee)
            self.queryset = self.queryset.filter(date__gte=self.start_date)
            self.queryset = self.queryset.filter(date__lte=self.end_date)

        return self.queryset
    
    
        
        
        
        
        
                