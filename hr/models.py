"""
Models to be use in the HR application
"""
import logging
from decimal import Decimal
from datetime import datetime, timedelta
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
    card_id = models.IntegerField(null=True)
    bank = models.TextField(blank=True, null=True)
    account_number = models.TextField(null=True, blank=True)
    government_id = models.TextField(null=True)
    
    class Meta:
        permissions = (('can_view_pay_rate', 'Can view pay rate'),)
                       
    @property
    def xname(self):
        try:
            return "{0} {1}".format(self.first_name, self.last_name or "")
        except Exception:
            return ""
            
    def log_attendance(self, start_time, end_time):
        """
        Creates a instance of the attendance class to track
        employee attendance
        
        Takes the arguments of start time and end time, and creates
        a new instance. Attendance instance will automatically calculate
        regular_time, overtime, and total_time.
        """
        
    def calculate_net_pay(self, start_date, end_date):
        """
        Calculates the total amount owed to the employee
        after wages and deductions
        """
        gross_pay = self._calculate_gross_pay(start_date, end_date)
        pay_after_social_security = self._apply_social_security_deduction(gross_pay)
        pay_after_tax = self._apply_tax_deduction(pay_after_social_security)
        
        net_pay = pay_after_tax
        
        return net_pay
             
    def _calculate_gross_pay(self, start_date, end_date):
        """
        Retrieve the pay due to the employee for the determine
        period pretax deductions
        """
        if self.pay_period.lower() == 'monthly':
            pay = self._calculate_salary_pay_for_pay_period(start_date, end_date)
        elif self.pay_period.lower() == 'daily':
            pay = self._calculate_daily_wages_for_pay_period(start_date, end_date)
        else:
            message = """
            Expecting pay to be classified by month or daily, not {0}
            """.format(self.pay_period)
            raise ValueError(message)
        
        #Debug Log
        message = "Gross pay for period {0} to {1} is {2} for {3}, a {4} employee"
        message = message.format(start_date.strftime('%B %d, %Y'),
                                 end_date.strftime('%B %d, %Y'),
                                 pay, 
                                 self.name,
                                 self.pay_period.lower())
        logger.debug(message)
        
        return pay
            
    def _calculate_salary_pay_for_pay_period(self, start_date, end_date):
        """
        Calculate the pay for a salaried employee within the pay period
        """
        period = end_date - start_date
        
        if period.days > 15:
            return Decimal(self.wage)
        else: 
            return Decimal(self.wage) / 2
            
    def _calculate_daily_wages_for_pay_period(self, start_date, end_date):
        attendances = Attendance.objects.filter(start_time__gte=start_date,
                                                end_time__lte=end_date,
                                                employee=self)
        
        message = "Worked for {0} days in period {1} to {2}"
        message = message.format(attendances.count(),
                                 start_date.strftime('%B %d, %Y'),
                                 end_date.strftime('%B %d, %Y'))
        logger.debug(message)
        
        wages = sum([self._calculate_daily_wages(a) for a in attendances])
        logger.debug(wages)
        
        return wages  
            
    def _calculate_daily_wages(self, attendance):
        """
        Calculates the daily wages based on attendance
        """
        #Get base pay
        pay = Decimal(self.wage) if attendance.total_time >= 8 else 8
        
        
        if attendance.start_time.isoweekday() == 7:
            pay = pay * Decimal('2')                                    
        
        logger.debug("Base pay for {0} is {1}".format(attendance.start_time.strftime('%B %d, %Y'),
                                                      pay))
                                                      
        if attendance.overtime > 0:
            
            rate = '3' if attendance.start_time.isoweekday() == 7 else '1.5'
            overtime_rate = Decimal(rate)
            
            logger.debug("Worked {0} overtime".format(attendance.overtime))
            overtime = attendance.overtime * ((Decimal(self.wage) / Decimal('8') * overtime_rate))
            logger.debug("Overtime pay for {0} is {1}".format(attendance.start_time.strftime('%B %d, %Y'),
                                                              overtime))
                                                              
            pay += overtime
            
        return pay
        
    def _apply_social_security_deduction(self, pay):
        """
        Deduct social security benefits from the pay
        
        -Deductions are currently 5% of the pay
        """
        return pay - (pay * Decimal('0.05') if pay * Decimal('0.05') < 750 else Decimal('750')) if self.legal else pay
        
    def _apply_tax_deduction(self, pay):
        """
        Deduct tax from the pay
        -Deductions are currently 500baht per person
        """
        return pay - Decimal('500') if self.legal else pay


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
    pay_rate = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    regular_pay = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    overtime_pay = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    doubletime_pay = models.DecimalField(decimal_places=2, max_digits=12, default=0)

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
        logger.debug('setter: {0}'.format(value))
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
        if self.start_time and self.end_time:
            self.calculate_times()
        
    def __init__(self, *args, **kwargs):
        """
        Override the initialization method
        """
        super(Attendance, self).__init__(*args, **kwargs)
        
        #Set standard timezone
        self.tz = timezone('Asia/Bangkok')
        
        if self.start_time and self.end_time:
            self.calculate_times()
                            
    def calculate_times(self):
        """
        wrapper for '_calculate_different_time_types'
        """
        self.pay_rate = self.pay_rate or self.employee.wage
        
        self.shift = self.shift or self.employee.shift
        
        if self.start_time and self.end_time:
            self._calculate_different_time_types()
        
    def _calculate_different_time_types(self):
        """
        Calculates the times to be work
        """
        # Calculate the total time for this attendance
        total_seconds = Decimal(str((self.end_time - self.start_time).total_seconds()))
        self.total_time = (total_seconds / Decimal('3600')) - Decimal('1')
        
        # Calculate the times for sundays
        if self.date.weekday() == 6:
            start = self.start_time.time() if self.start_time.time() > self.shift.start_time else self.shift.start_time
            end = self.end_time.time()
        
            time_delta = self._calculate_timedelta(start, end)
            self.total_time = (Decimal(str(time_delta.total_seconds())) / Decimal('3600')) - Decimal('1')

            # Calculate whether an employee is late or not
            if self.total_time > Decimal('8') and self.start_time.hour == self.shift.start_time.hour and self.start_time.minute <= 10:
                self.doubletime = Decimal('8')
            else:
                self.doubletime = (Decimal(str(self._calculate_timedelta(self.start_time.time(), self.shift.end_time).total_seconds())) / Decimal('3600')) - 1
        
        # Calculate the times for nonsundays
        else:
            # Calculate times if overtime is enabled
            if self.enable_overtime:
                start = self.start_time.time() if self.start_time.time() > self.shift.start_time else self.shift.start_time
                end = self.end_time.time()
            
                time_delta = self._calculate_timedelta(start, end)
                self.total_time = (Decimal(str(time_delta.total_seconds())) / Decimal('3600')) - Decimal('1')

                if self.total_time > Decimal('8'):
                    self.regular_time = Decimal('8')
                    self.overtime = self.total_time - self.regular_time
                    logger.warn(self.overtime)
        
            # Calculate the times if overtime is not enabled
            else:
                start = self.start_time.time() if self.start_time.time() > self.shift.start_time else self.shift.start_time
                end = self.end_time.time() if self.end_time.time() < self.shift.end_time else self.shift.end_time
            
                time_delta = self._calculate_timedelta(start, end)
            
                self.regular_time = (Decimal(str(time_delta.total_seconds())) / Decimal('3600')) - Decimal('1')
                self.overtime = 0
                self.total_time = self.regular_time
            
        self.save()
            
    def _calculate_timedelta(self, t1, t2):
        """
        Calculate the differences in times
        """
        fmt = '%H:%M:%S'
        s1 = t1.strftime(fmt)
        s2 = t2.strftime(fmt)
        tdelta = datetime.strptime(s2, fmt) - datetime.strptime(s1, fmt)
        
        return tdelta
        
    def _calculate_overtime(self):
        """
        Calculates the number of overtime hours due to the employee
        
        Rules:
        -Must work at least 1 hour past end of shift
        -Overtime granted by every half hour. Must work past half hour
        Ex. worked 1.66 overtime becomes 1.5. worked 1.25 becomes 1
        """
        excess_time = self.total_time - self.regular_time
        logger.debug("excess: {0}".format(excess_time))
        
        self.overtime = floor(excess_time * 2) / 2 if excess_time >= 1 else 0
        self.overtime = Decimal(str(self.overtime))
        
    def _calculate_pay(self):
        """
        Calculate the daily pay
        
        Calculates the regular pay first based on if the employee worked 8 hours
        and if the employee was late
        """
        # Get the pay rate based on if the day is Sunday
        if self.date.weekday() == 6:
            pay_rate = self.pay_rate * Decimal('2')
            # Calculate wage to be paid for this date based on if late or hours less than 8 hours
            if self.regular_time == Decimal('8'):
                self.doubletime_pay = pay_rate
            elif self.start_time.hour == self.shift.start_time.hour and self.start_time.minute <= 10:
                self.doubletime_pay = pay_rate
            else:
                self.doubletime_pay = pay_rate * self.doubletime
                
        else:
            pay_rate = self.pay_rate
            # Calculate wage to be paid for this date based on if late or hours less than 8 hours
            if self.regular_time == Decimal('8'):
                self.regular_pay = pay_rate
            elif self.start_time.hour == self.shift.start_time.hour and self.start_time.minute <= 10:
                self.regular_pay = pay_rate
            else:
                self.regular_pay = pay_rate * self.regular_time
            
        
        
            # Calculate the overtime pay for non Sunday dates
            if self.enable_overtime:
                self.overtime_pay = ((pay_rate / Decimal('8')) * Decima('1.5')) * self.overtime

                