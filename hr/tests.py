"""
Testing File for HR application
"""
import logging
import unittest
from decimal import Decimal
from datetime import date, datetime, time

from django.test import TestCase
from pytz import timezone
from rest_framework.test import APITestCase, APIClient

from hr.models import Employee, Attendance, Shift, Payroll, PayRecord


logger = logging.getLogger(__name__)


# Create your tests here.
employee1_data = {
    'name': 'test1',
    'legal': True,
    'department': 'front office',
    'telephone': '029987465',
    'wage': Decimal('18000'),
    'pay_period': 'Monthly',
    'employement_date': date.today(),
    'social_security_id': '123-33-333',
    'incentive_pay': Decimal('50'),
    'payment_option': 'direct deposit',
    'bank': 'thanachart',
    'account_number': '13-232342-234'
}

employee2_data = {
    'name': 'test2',
    'legal': True,
    'department': 'painting',
    'telephone': '0983337654',
    'wage': Decimal('550'),
    'pay_period': 'Daily',
    'employement_date': date.today(),
    'social_security_id': '123-33-333',
    'incentive_pay': Decimal('30'),
    'payment_option': 'cash'
}

employee3_data = {
    'name': 'test3',
    'legal': False,
    'department': 'carpentry',
    'telephone': '0834679880',
    'wage': Decimal('300'),
    'pay_period': 'Daily',
    'employement_date': date.today(),
    'social_security_id': '123-33-333',
    'payment_option': 'cash'
}

employee4_data = {
    'name': 'test4',
    'legal': True,
    'department': 'painting',
    'telephone': '0983337654',
    'wage': Decimal('550'),
    'pay_period': 'Daily',
    'employement_date': date.today(),
    'social_security_id': '123-33-333',
    'incentive_pay': Decimal('30'),
    'location': 'cambodia',
    'payment_option': 'direct deposit',
    'bank': 'thanachart',
    'account_number': '13-33244-22234'
}

manager_data = {
    'name': 'manager1',
    'legal': True,
    'department': 'painting',
    'telephone': '029987465',
    'wage': Decimal('650'),
    'pay_period': 'daily',
    'employement_date': date.today(),
    'social_security_id': '123-33-333',
    'incentive_pay': Decimal('50'),
    'manager_stipend': 1500,
    'payment_option': 'direct deposit',
    'bank': 'thanachart',
    'account_number': '13-2323242342-444'
}


class AttendanceTest(APITestCase):
    """
    Testing class for attendance
    """
    def setUp(self):
        """
        Set up the Testing clas:
        """
        super(AttendanceTest, self).setUp()
        
        #self.client.client.login(username='test', password='test')
        
        self.shift = Shift(start_time=time(8, 0),
                           end_time=time(17, 0))
        self.shift.save()
        
        self.employee = Employee(shift=self.shift, **employee2_data)
        self.employee.save()
        
        # Regular attendance
        self.attendance = Attendance(date=date(2014, 7, 1),
                                     start_time=timezone('Asia/Bangkok').localize(datetime(2014, 7, 1, 7, 30, 0)),
                                     end_time=timezone('Asia/Bangkok').localize(datetime(2014, 7, 1, 23, 33, 0)), 
                                     employee=self.employee,
                                     shift=self.shift)
                                     
        self.attendance.save()
        
        # Sunday attendance
        self.sunday_attendance = Attendance(date=date(2016, 2, 7),
                                            start_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 7, 8, 02, 0)),
                                            end_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 7, 23, 15, 0)), 
                                            employee=self.employee,
                                            shift=self.shift)
        self.sunday_attendance.save()
        
        self.tz = timezone('Asia/Bangkok')
        
    def test_start_time_property(self):
        """Test that the getter and setter for start time work properly
        """
        a = Attendance(employee=self.employee, date=date(2016, 3, 21))
        d1 = datetime(2016, 3, 21, 8, 11, 0)
        
        # Test start time without timezone
        a.start_time = d1
        self.assertEqual(a._start_time, self.tz.localize(d1))
        self.assertEqual(a.start_time, self.tz.localize(d1))
        
        # Test start time with timezone
        a.start_time = self.tz.localize(d1)
        self.assertEqual(a._start_time, self.tz.localize(d1))
        self.assertEqual(a.start_time, self.tz.localize(d1))
        
    def test_end_time_property(self):
        """Test that the getter and setter for start time work properly
        """
        a = Attendance(employee=self.employee, date=date(2016, 3, 21))
        d1 = datetime(2016, 3, 21, 15, 29, 0)
        
        # Test start time without timezone
        a.end_time = d1
        self.assertEqual(a._end_time, self.tz.localize(d1))
        self.assertEqual(a.end_time, self.tz.localize(d1))
        
        # Test start time with timezone
        a.end_time = self.tz.localize(d1)
        self.assertEqual(a._end_time, self.tz.localize(d1))
        self.assertEqual(a.end_time, self.tz.localize(d1))
                                            
    def test_regular_attedance_regular_hours(self):
        """Test the regular hours of a regular attedance
        """
        self.attendance.calculate_times()
        self.assertEqual(self.attendance.regular_time, Decimal('8.0'))
        self.assertEqual(self.attendance.overtime, Decimal('0'))
        
    def test_regular_attedance_with_overtime_enabled(self):
        """Test the regular hours of a regular attedance
        """
        self.attendance.enable_overtime = True
        
        self.attendance.calculate_times()
        self.assertEqual(self.attendance.regular_time, Decimal('8.0'))
        self.assertEqual(self.attendance.overtime, Decimal('6.5'))
        
    def test_regular_attendance_gross_wage(self):
        """Test the gross wage of a regular attendance
        """
        self.attendance.calculate_times()
        self.attendance.calculate_gross_wage()
        
        self.assertEqual(self.attendance.regular_pay, Decimal('550'))
        self.assertEqual(self.attendance.overtime_pay, Decimal('0'))
        self.assertEqual(self.attendance.lunch_pay, Decimal('0'))
        
        self.assertEqual(self.attendance.gross_wage, Decimal('550'))
        
    def test_regular_attendance_gross_wage_with_overtime_enabled(self):
        """Test the gross wage of a regular attendance with overtime enabled
        """
        self.attendance.enable_overtime = True
        self.attendance.calculate_times()
        self.attendance.calculate_gross_wage()
        
        self.assertEqual(self.attendance.regular_pay, Decimal('550'))
        
        # Calculate expected overtime pay
        ot_rate = (Decimal('550') / Decimal('8')) * Decimal('1.5')
        self.assertEqual(self.attendance.overtime_pay, ot_rate * Decimal('6.5'))
        self.assertEqual(self.attendance.lunch_pay, Decimal('0'))
        
        # Test gross wage
        self.assertEqual(self.attendance.gross_wage, Decimal('550') + (ot_rate * Decimal('6.5')))
        
    def test_regular_attendance_net_wage(self):
        """Test the gross wage of a regular attendance
        """
        self.attendance.calculate_times()
        self.attendance.calculate_net_wage()
        
        self.assertEqual(self.attendance.gross_wage, Decimal('550'))
        self.assertEqual(self.attendance.reimbursement, Decimal('30'))
        self.assertEqual(self.attendance.net_wage, Decimal('580'))
        
    def test_regular_attendance_net_wage_with_lunch(self):
        """Test the gross wage of a regular attendance
        """
        self.attendance.receive_lunch_overtime = True
        self.attendance.calculate_times()
        self.attendance.calculate_net_wage()
        
        self.assertEqual(self.attendance.gross_wage, Decimal('653.125'))
        self.assertEqual(self.attendance.reimbursement, Decimal('60'))
        self.assertEqual(self.attendance.net_wage, Decimal('713.125'))
        
    def test_regular_attendance_net_wage_where_clockin_late(self):
        """Test the net wage where an employee is late
        """
        logger.debug("\n\n\n\nTesting late clocking for regular attendance\n\n\n")
        
        # Change start time so employee is late
        self.attendance.start_time = self.tz.localize(datetime(2014, 7, 1, 8, 15, 0))
        self.attendance.calculate_times()
        self.attendance.calculate_net_wage()
        
        self.assertEqual(self.attendance.regular_time, Decimal('7.5'))
        self.assertEqual(self.attendance.reimbursement, Decimal('0'))
        self.assertEqual(self.attendance.net_wage, Decimal('515.625'))
    
    def test_sunday_attendance_regular_hours(self):
        """Test the regular hours of a regular attedance
        """
        logger.debug("\n\n\n\nTesting Sunday Regular attendance hours\n\n\n")
        self.sunday_attendance.calculate_times()
        self.assertEqual(self.sunday_attendance.regular_time, Decimal('8.0'))
        self.assertEqual(self.sunday_attendance.overtime, Decimal('0'))
        
    def test_sunday_attendance_with_overtime_enabled(self):
        """Test the regular hours of a regular attedance
        """
        self.sunday_attendance.enable_overtime = True
        
        self.sunday_attendance.calculate_times()
        self.assertEqual(self.sunday_attendance.regular_time, Decimal('8.0'))
        self.assertEqual(self.sunday_attendance.overtime, Decimal('6'))
        
    def test_sunday_attendance_gross_wage(self):
        """Test the gross wage of a sunday attendance
        """
        self.sunday_attendance.calculate_times()
        self.sunday_attendance.calculate_gross_wage()
        
        self.assertEqual(self.sunday_attendance.regular_pay, Decimal('1100'))
        self.assertEqual(self.sunday_attendance.overtime_pay, Decimal('0'))
        self.assertEqual(self.sunday_attendance.lunch_pay, Decimal('0'))
        
        self.assertEqual(self.sunday_attendance.gross_wage, Decimal('1100'))
        
    def test_sunday_attendance_gross_wage_with_overtime_enabled(self):
        """Test the gross wage of a sunday attendance
        """
        self.sunday_attendance.enable_overtime = True
        self.sunday_attendance.calculate_times()
        self.sunday_attendance.calculate_gross_wage()
        
        self.assertEqual(self.sunday_attendance.regular_pay, Decimal('1100'))
        
        # Calculate expected overtime pay
        ot_rate = (Decimal('550') / Decimal('8')) * Decimal('3')
        self.assertEqual(self.sunday_attendance.overtime_pay, ot_rate * Decimal('6'))
        self.assertEqual(self.sunday_attendance.lunch_pay, Decimal('0'))
        
        # Test gross wage
        self.assertEqual(self.sunday_attendance.gross_wage, Decimal('1100') + (ot_rate * Decimal('6')))
        

class PayRecordTest(APITestCase):
    """Test class for Payrecord"""
    
    def setUp(self):
        """Setup for testing
        
        Employees:
        - 1. Daily employee
        -   1.1 Attendances 
        - 2. Salaried employee
        -   2.1 Attendances
        - 3. Daily Manager
        -   3.1 Attendances
        """
        logger.debug("\n\nBegin Setup\n\n")
        
        self.shift = Shift(start_time=time(8, 0, tzinfo=timezone('Asia/Bangkok')),
                           end_time=time(17, 0, tzinfo=timezone('Asia/Bangkok')))
        self.shift.save()
        
        self.employee1 = Employee.objects.create(**employee2_data)
        self.employee2 = Employee.objects.create(**employee1_data)
        self.employee3 = Employee.objects.create(shift=self.shift, **employee4_data)
        self.manager = Employee.objects.create(**manager_data)
        
        
        logger.warn(self.shift)
        # Create attendances for first half of the month
        for i in xrange(0, 7):
            a_date = date(2016, 2, 1 + i)
            
            # Create attendances for daily employee
            a = Attendance.objects.create(date=a_date,
                                          start_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 1 + i, 7, 30, 0)),
                                          end_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 1 + i, 17, 15, 0)), 
                                          employee=self.employee1,
                                          shift=self.shift)
            a.calculate_times()
            a.calculate_net_wage()
            a.save()
             
            # Create attendances for monthly employee
            a = Attendance.objects.create(date=a_date,
                                          start_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 1 + i, 7, 30, 0)),
                                          end_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 1 + i, 17, 15, 0)),
                                          employee=self.employee2,
                                          shift=self.shift)
            a.calculate_times()
            a.calculate_net_wage()
            a.save()
            
            # Create attendances for daily employee in cambodia
            a = Attendance.objects.create(date=a_date,
                                          start_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 1 + i, 7, 30, 0)),
                                          end_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 1 + i, 17, 15, 0)),
                                          employee=self.employee3,
                                          shift=self.shift,
                                          cambodia=True)
            a.calculate_times()
            a.calculate_net_wage()
            a.save()
            
            # Create attendances for daily manager
            a = Attendance.objects.create(date=a_date,
                                          start_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 1 + i, 7, 30, 0)),
                                          end_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 1 + i, 17, 15, 0)),
                                          employee=self.manager,
                                          shift=self.shift)
            a.calculate_times()
            a.calculate_net_wage()
            a.save()
            
        # Create the attendances for the latter half of the month
        for i in xrange(0, 6):
            a_date = date(2016, 2, 15 + i)
            
            # Create attendances for daily employee
            a = Attendance.objects.create(date=a_date,
                                          start_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 1 + i, 7, 30, 0)),
                                          end_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 1 + i, 17, 15, 0)),
                                          employee=self.employee1,
                                          shift=self.shift)
            a.calculate_times()
            a.calculate_net_wage()
            a.save()
             
            # Create attendances for monthly employee
            a = Attendance.objects.create(date=a_date,
                                          start_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 1 + i, 7, 30, 0)),
                                          end_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 1 + i, 17, 15, 0)),
                                          employee=self.employee2,
                                          shift=self.shift)
            a.calculate_times()
            a.calculate_net_wage()
            a.save()
            
            # Create attendances for daily employee in cambodia
            a = Attendance.objects.create(date=a_date,
                                          start_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 1 + i, 7, 30, 0)),
                                          end_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 1 + i, 17, 15, 0)),
                                          employee=self.employee3,
                                          shift=self.shift,
                                          cambodia=True)
            a.calculate_times()
            a.calculate_net_wage()
            a.save()
            
            # Create attendances for daily manager
            a = Attendance.objects.create(date=a_date,
                                          start_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 1 + i, 7, 30, 0)),
                                          end_time=timezone('Asia/Bangkok').localize(datetime(2016, 2, 1 + i, 17, 15, 0)),
                                          employee=self.manager,
                                          shift=self.shift)
            a.calculate_times()
            a.calculate_net_wage()
            a.save()
            
        logger.debug("\n\nEnd Setup\n\n")
        
        
    def test_gross_wage_hourly_employee(self):
        """Test calculate the gross wage of a pay record
        """
        record = PayRecord.objects.create(self.employee1, 
                                          start_date=date(2016, 2, 1),
                                          end_date=date(2016, 2, 10))
        gw = record.calculate_gross_wage()
        self.assertEqual(gw, Decimal('4400'))
        
    def test_net_wage_hourly_employee(self):
        """Test calculate the net wage of a pay record
        """
        record = PayRecord.objects.create(self.employee1, 
                                          start_date=date(2016, 2, 1),
                                           end_date=date(2016, 2, 10))
        nw = record.calculate_net_wage()
        self.assertEqual(record.stipend, Decimal('210'))
        self.assertEqual(record.manager_stipend, Decimal('0'))
        self.assertEqual(record.deductions, Decimal('0'))
        self.assertEqual(record.social_security_withholding, Decimal('0'))
        self.assertEqual(nw, Decimal('4610'))
        
    def test_net_wage_hourly_employee_end_month(self):
        """Test calculate the net wage of a pay record
        """
        record = PayRecord.objects.create(self.employee1, 
                                          start_date=date(2016, 2, 11),
                                           end_date=date(2016, 2, 25))
        nw = record.calculate_net_wage()
        self.assertEqual(record.stipend, Decimal('180'))
        self.assertEqual(record.manager_stipend, Decimal('0'))
        self.assertEqual(record.deductions, Decimal('0'))
        self.assertEqual(record.social_security_withholding, Decimal('385'))
        self.assertEqual(nw, Decimal('3095'))
        
    def test_gross_wage_hourly_employee_in_cambodia(self):
        """Test calculate the gross wage of a pay record
        """
        record = PayRecord.objects.create(self.employee3, 
                                          start_date=date(2016, 2, 1),
                                          end_date=date(2016, 2, 10))
        gw = record.calculate_gross_wage()
        self.assertEqual(gw, Decimal('9050'))
        
    def test_net_wage_hourly_employee_in_cambodia(self):
        """Test calculate the net wage of a pay record
        """
        record = PayRecord.objects.create(self.employee3, 
                                          start_date=date(2016, 2, 1),
                                           end_date=date(2016, 2, 10))
        nw = record.calculate_net_wage()
        self.assertEqual(record.stipend, Decimal('300'))
        self.assertEqual(record.manager_stipend, Decimal('0'))
        self.assertEqual(record.deductions, Decimal('0'))
        self.assertEqual(record.social_security_withholding, Decimal('0'))
        self.assertEqual(nw, Decimal('9350'))
    
    def test_gross_wage_hourly_employee_in_cambodia_end_month(self):
        """Test calculate the net wage of a pay record
        """
        record = PayRecord.objects.create(self.employee3, 
                                          start_date=date(2016, 2, 11),
                                           end_date=date(2016, 2, 25))
        gw = record.calculate_gross_wage()
        self.assertEqual(gw, Decimal('11050'))
        
    def test_net_wage_hourly_employee_in_cambodia_end_month(self):
        """Test calculate the net wage of a pay record
        """
        record = PayRecord.objects.create(self.employee3, 
                                          start_date=date(2016, 2, 11),
                                           end_date=date(2016, 2, 25))
        nw = record.calculate_net_wage()
        self.assertEqual(record.stipend, Decimal('390'))
        self.assertEqual(record.manager_stipend, Decimal('0'))
        self.assertEqual(record.deductions, Decimal('0'))
        self.assertEqual(record.social_security_withholding, Decimal('750'))
        self.assertEqual(nw, Decimal('10690'))
        
    def test_gross_wage_salaried_employee(self):
        """Test calculate the gross wage of a pay record
        """
        record = PayRecord.objects.create(self.employee2, 
                                          start_date=date(2016, 2, 1),
                                          end_date=date(2016, 2, 10))
        gw = record.calculate_gross_wage()
        self.assertEqual(gw, Decimal('10200'))
        
    def test_net_wage_salaried_employee(self):
        """Test calculate the net wage of a pay record
        """
        record = PayRecord.objects.create(self.employee2, 
                                          start_date=date(2016, 2, 1),
                                          end_date=date(2016, 2, 10))
        nw = record.calculate_net_wage()
        self.assertEqual(nw, Decimal('10550'))
        self.assertEqual(record.reimbursements, Decimal('350'))
        self.assertEqual(record.social_security_withholding, Decimal('0'))
        
    def test_gross_wage_manager(self):
        """Test calculate the gross wage of a pay record
        """
        record = PayRecord.objects.create(self.manager, 
                                          start_date=date(2016, 2, 1),
                                          end_date=date(2016, 2, 10))
        gw = record.calculate_gross_wage()
        self.assertEqual(gw, Decimal('5200'))
        
    def test_net_wage_manager_employee(self):
        """Test calculate the net wage of a pay record
        """
        record = PayRecord.objects.create(self.manager, 
                                          start_date=date(2016, 2, 1),
                                          end_date=date(2016, 2, 10))
        nw = record.calculate_net_wage()
        self.assertEqual(nw, Decimal('5550.00'))
        self.assertEqual(record.reimbursements, Decimal('350'))
        self.assertEqual(record.social_security_withholding, Decimal('0'))
        
    def test_net_wage_manager_end_month(self):
        """Test calculate the net wage of a pay record
        """
        record = PayRecord.objects.create(self.manager, 
                                          start_date=date(2016, 2, 11),
                                          end_date=date(2016, 2, 25))
        nw = record.calculate_net_wage()
        self.assertEqual(record.reimbursements, Decimal('300'))
        self.assertEqual(record.social_security_withholding, Decimal('455'))
        self.assertEqual(nw, Decimal('5245'))


class PayrollTest(APITestCase):
    
    def setUp(self):
        """Setup for testing
        
        Employees:
        - 1. Daily employee
        -   1.1 Attendances 
        - 2. Salaried employee
        -   2.1 Attendances
        - 3. Daily Manager
        -   3.1 Attendances
        """
        self.shift = Shift(start_time=time(8, 0),
                           end_time=time(17, 0))
        self.shift.save()
        
        self.employee1 = Employee.objects.create(**employee2_data)
        self.employee2 = Employee.objects.create(**employee1_data)
        self.employee3 = Employee.objects.create(**employee4_data)
        self.manager = Employee.objects.create(**manager_data)
        
        # Create attendances for first half of the month
        for i in xrange(0, 6):
            a_date = date(2016, 2, 1 + i)
            
            # Create attendances for daily employee
            a = Attendance.objects.create(date=a_date,
                                          start_time=datetime(2016, 2, 1 + i, 7, 30, 0, tzinfo=timezone('Asia/Bangkok')),
                                          end_time=datetime(2016, 2, 1 + i, 17, 15, 0, tzinfo=timezone('Asia/Bangkok')), 
                                          employee=self.employee1,
                                          shift=self.shift)
            a.calculate_times()
            a.calculate_net_wage()
            a.save()
             
            # Create attendances for monthly employee
            a = Attendance.objects.create(date=a_date,
                                          start_time=datetime(2016, 2, 1 + i, 7, 30, 0, tzinfo=timezone('Asia/Bangkok')),
                                          end_time=datetime(2016, 2, 1 + i, 17, 15, 0, tzinfo=timezone('Asia/Bangkok')), 
                                          employee=self.employee2,
                                          shift=self.shift)
            a.calculate_times()
            a.calculate_net_wage()
            a.save()
            
            # Create attendances for daily employee in cambodia
            a = Attendance.objects.create(date=a_date,
                                          start_time=datetime(2016, 2, 1 + i, 7, 30, 0, tzinfo=timezone('Asia/Bangkok')),
                                          end_time=datetime(2016, 2, 1 + i, 17, 15, 0, tzinfo=timezone('Asia/Bangkok')), 
                                          employee=self.employee3,
                                          shift=self.shift)
            a.calculate_times()
            a.calculate_net_wage()
            a.save()
            
            # Create attendances for daily manager
            a = Attendance.objects.create(date=a_date,
                                          start_time=datetime(2016, 2, 1 + i, 7, 30, 0, tzinfo=timezone('Asia/Bangkok')),
                                          end_time=datetime(2016, 2, 1 + i, 17, 15, 0, tzinfo=timezone('Asia/Bangkok')), 
                                          employee=self.manager,
                                          shift=self.shift)
            a.calculate_times()
            a.calculate_net_wage()
            a.save()
            
        # Create the attendances for the latter half of the month
        for i in xrange(0, 6):
            a_date = date(2016, 2, 15 + i)
            
            # Create attendances for daily employee
            a = Attendance.objects.create(date=a_date,
                                          start_time=datetime(2016, 2, 15 + i, 7, 30, 0, tzinfo=timezone('Asia/Bangkok')),
                                          end_time=datetime(2016, 2, 15 + i, 17, 15, 0, tzinfo=timezone('Asia/Bangkok')), 
                                          employee=self.employee1,
                                          shift=self.shift)
            a.calculate_times()
            a.calculate_net_wage()
            a.save()
             
            # Create attendances for monthly employee
            a = Attendance.objects.create(date=a_date,
                                          start_time=datetime(2016, 2, 15 + i, 7, 30, 0, tzinfo=timezone('Asia/Bangkok')),
                                          end_time=datetime(2016, 2, 15 + i, 17, 15, 0, tzinfo=timezone('Asia/Bangkok')), 
                                          employee=self.employee2,
                                          shift=self.shift)
            a.calculate_times()
            a.calculate_net_wage()
            a.save()
            
            # Create attendances for daily employee in cambodia
            a = Attendance.objects.create(date=a_date,
                                          start_time=datetime(2016, 2, 15 + i, 7, 30, 0, tzinfo=timezone('Asia/Bangkok')),
                                          end_time=datetime(2016, 2, 15 + i, 17, 15, 0, tzinfo=timezone('Asia/Bangkok')), 
                                          employee=self.employee3,
                                          shift=self.shift)
            a.calculate_times()
            a.calculate_net_wage()
            a.save()
            
            # Create attendances for daily manager
            a = Attendance.objects.create(date=a_date,
                                          start_time=datetime(2016, 2, 15 + i, 7, 30, 0, tzinfo=timezone('Asia/Bangkok')),
                                          end_time=datetime(2016, 2, 15 + i, 17, 15, 0, tzinfo=timezone('Asia/Bangkok')), 
                                          employee=self.manager,
                                          shift=self.shift)
            a.calculate_times()
            a.calculate_net_wage()
            a.save()
            
    def test_document_creation(self):
        """Test the creation of documents for this payroll
        """
        start_date = date(2016, 1, 26)
        end_date = date(2016, 2, 10)
        
        payroll = Payroll.objects.create(start_date, end_date)
        
    def test_document_creation_end_month(self):
        """Test the creation of documents for this payroll
        """
        start_date = date(2016, 2, 11)
        end_date = date(2016, 2, 25)
        
        payroll = Payroll.objects.create(start_date, end_date)

        
@unittest.skip("ok")           
class Employee1Test(APITestCase):
    """
    Testing class for salaried workers
    """
    
    def setUp(self):
        """
        Set up the Testing class:
        
        -self.employee = salary worker
        -self.employee = daily worker
        -self.employee3 = daily worker with no legal status
        """
        super(Employee1Test, self).setUp()
        self.employee = Employee(**employee1_data)
        self.employee.save()
        
    def test_calculate_gross_pay_salary(self):
        """
        Test that the pay is correct for 2 week period of
        a salaried worker
        """
        #test 2 weeks pay
        gross_pay = self.employee._calculate_gross_pay(date(2014, 7, 1), date(2014, 7, 15))
        self.assertEqual(gross_pay, 9000)
        
        #Test 1 month pay
        gross_pay = self.employee._calculate_gross_pay(date(2014, 7, 1), date(2014, 7, 31))
        self.assertEqual(gross_pay, 18000)
        
    def test_social_security_deduction(self):
        """
        Test whether the social security is properly deducted
        """
        pay_post_deduction = self.employee._apply_social_security_deduction(Decimal('10000'))
        self.assertEqual(pay_post_deduction, 9500)
    
    def test_tax_deduction(self):
        """
        Test whether the tax is propery deducted
        
        -tax is currently set for 500baht per person
        """
        pay_post_tax = self.employee._apply_tax_deduction(Decimal('9500'))
        self.assertEqual(pay_post_tax, 9000)
    
    def test_net_pay(self):
        """
        Test whether the net pay is calculated property
        """
        net_pay = self.employee.calculate_net_pay(date(2014, 7, 1), date(2014, 7, 15))
        self.assertEqual(net_pay, 8050)
    

@unittest.skip("ok")           
class Employee2Test(APITestCase):
    """
    Testing class for daily worker
    """
    
    def setUp(self):
        """
        Set up the Testing class:
        
        -self.employee = salary worker
        -self.employee = daily worker
        -self.employee3 = daily worker with no legal status
        """
        super(Employee2Test, self).setUp()
        self.employee = Employee(**employee2_data)
        self.employee.save()
        
        for day in xrange(1, 15):
            hour = 20 if day % 2 > 0 else 17
        
            a = Attendance(employee=self.employee,
                           start_time=datetime(2014, 7, day, 8, 0),
                           end_time=datetime(2014, 7, day, hour, 0))
            a.save()
            
        
    def test_calculate_daily_wage(self):
        """
        Test that the daily wage is correctly calculated
        
        Tests:
        -regular with perfect in out
        -regular day with slightly over in out
        -day with over time
        -sunday with no overtime
        -sunday with overtime
        """
        #Regular day with perfect in out
        a = Attendance(employee=self.employee,
                       start_time=datetime(2014, 7, 1, 8, 0),
                       end_time=datetime(2014, 7, 1, 17, 0))
        wage = self.employee._calculate_daily_wages(a)
        
        self.assertEqual(wage, 550)
        
        #Regular day with slightly imperfect in out
        a = Attendance(employee=self.employee,
                       start_time=datetime(2014, 7, 1, 8, 0),
                       end_time=datetime(2014, 7, 1, 17, 14))
        wage = self.employee._calculate_daily_wages(a)
        
        self.assertEqual(wage, 550)
        
        #Day with over time
        a = Attendance(employee=self.employee,
                       start_time=datetime(2014, 7, 1, 8, 0),
                       end_time=datetime(2014, 7, 1, 20, 0))
        self.assertEqual(a.total_time, 11)
        self.assertEqual(a.overtime, 3)
        self.assertEqual(a.regular_time, 8)
        wage = self.employee._calculate_daily_wages(a)
        
        self.assertEqual(wage, 859.375)
        
        #Sunday with no overtime
        a = Attendance(employee=self.employee,
                       start_time=datetime(2014, 7, 6, 8, 0),
                       end_time=datetime(2014, 7, 6, 17, 0))
        self.assertEqual(a.total_time, 8)
        self.assertEqual(a.overtime, 0)
        self.assertEqual(a.regular_time, 8)
        wage = self.employee._calculate_daily_wages(a)
        self.assertEqual(wage, 1100)
        
        #Sunday with over time
        a = Attendance(employee=self.employee,
                       start_time=datetime(2014, 7, 6, 8, 0),
                       end_time=datetime(2014, 7, 6, 20, 0))
        self.assertEqual(a.total_time, 11)
        self.assertEqual(a.overtime, 3)
        self.assertEqual(a.regular_time, 8)
        wage = self.employee._calculate_daily_wages(a)
        self.assertEqual(wage, 1718.75)
    
    def test_calculate_gross_pay_wage(self):
        """
        Test that the pay is correct for 2 week period of
        a salaried worker
        """
        #test 2 weeks pay
        gross_pay = self.employee._calculate_gross_pay(date(2014, 7, 1), date(2014, 7, 15))
        self.assertEqual(gross_pay, 11275)
        
        #Test 1 month pay
        gross_pay = self.employee._calculate_gross_pay(date(2014, 7, 1), date(2014, 7, 31))
        self.assertEqual(gross_pay, 11275)
        
    def test_social_security_deduction(self):
        """
        Test whether the social security is properly deducted
        """
        pay_post_deduction = self.employee._apply_social_security_deduction(Decimal('10000'))
        self.assertEqual(pay_post_deduction, 9500)
    
    def test_tax_deduction(self):
        """
        Test whether the tax is propery deducted
        
        -tax is currently set for 500baht per person
        """
        pay_post_tax = self.employee._apply_tax_deduction(Decimal('9500'))
        self.assertEqual(pay_post_tax, 9000)
    
    def test_net_pay(self):
        """
        Test whether the net pay is calculated property
        """
        net_pay = self.employee.calculate_net_pay(date(2014, 7, 1), date(2014, 7, 15))
        self.assertEqual(net_pay, 10211.25)
        

@unittest.skip("ok")        
class Employee3Test(APITestCase):
    """
    Testing class for daily worker
    """
    
    def setUp(self):
        """
        Set up the Testing class:
        
        -self.employee = salary worker
        -self.employee = daily worker
        -self.employee3 = daily worker with no legal status
        """
        super(Employee3Test, self).setUp()
        self.employee = Employee(**employee3_data)
        self.employee.save()
        
        for day in xrange(1, 15):
            hour = 20 if day % 2 > 0 else 17
        
            a = Attendance(employee=self.employee,
                           start_time=datetime(2014, 7, day, 8, 0),
                           end_time=datetime(2014, 7, day, hour, 0))
            a.save()
            
        
    def test_calculate_daily_wage(self):
        """
        Test that the daily wage is correctly calculated
        
        Tests:
        -regular with perfect in out
        -regular day with slightly over in out
        -day with over time
        -sunday with no overtime
        -sunday with overtime
        """
        #Regular day with perfect in out
        a = Attendance(employee=self.employee,
                       start_time=datetime(2014, 7, 1, 8, 0),
                       end_time=datetime(2014, 7, 1, 17, 0))
        wage = self.employee._calculate_daily_wages(a)
        
        self.assertEqual(wage, 300)
        
        #Regular day with slightly imperfect in out
        a = Attendance(employee=self.employee,
                       start_time=datetime(2014, 7, 1, 8, 0),
                       end_time=datetime(2014, 7, 1, 17, 14))
        wage = self.employee._calculate_daily_wages(a)
        
        self.assertEqual(wage, 300)
        
        #Day with over time
        a = Attendance(employee=self.employee,
                       start_time=datetime(2014, 7, 1, 8, 0),
                       end_time=datetime(2014, 7, 1, 20, 0))
        self.assertEqual(a.total_time, 11)
        self.assertEqual(a.overtime, 3)
        self.assertEqual(a.regular_time, 8)
        wage = self.employee._calculate_daily_wages(a)
        
        self.assertEqual(wage, 468.75)
        
        #Sunday with no overtime
        a = Attendance(employee=self.employee,
                       start_time=datetime(2014, 7, 6, 8, 0),
                       end_time=datetime(2014, 7, 6, 17, 0))
        self.assertEqual(a.total_time, 8)
        self.assertEqual(a.overtime, 0)
        self.assertEqual(a.regular_time, 8)
        wage = self.employee._calculate_daily_wages(a)
        self.assertEqual(wage, 600)
        
        #Sunday with over time
        a = Attendance(employee=self.employee,
                       start_time=datetime(2014, 7, 6, 8, 0),
                       end_time=datetime(2014, 7, 6, 20, 0))
        self.assertEqual(a.total_time, 11)
        self.assertEqual(a.overtime, 3)
        self.assertEqual(a.regular_time, 8)
        wage = self.employee._calculate_daily_wages(a)
        self.assertEqual(wage, 937.5)
    
    def test_calculate_gross_pay_wage(self):
        """
        Test that the pay is correct for 2 week period of
        a salaried worker
        """
        #test 2 weeks pay
        gross_pay = self.employee._calculate_gross_pay(date(2014, 7, 1), date(2014, 7, 15))
        self.assertEqual(gross_pay, 6150)
        
        #Test 1 month pay
        gross_pay = self.employee._calculate_gross_pay(date(2014, 7, 1), date(2014, 7, 31))
        self.assertEqual(gross_pay, 6150)
        
    def test_social_security_deduction(self):
        """
        Test whether the social security is properly deducted
        """
        pay_post_deduction = self.employee._apply_social_security_deduction(Decimal('10000'))
        self.assertEqual(pay_post_deduction, 10000)
    
    def test_tax_deduction(self):
        """
        Test whether the tax is propery deducted
        
        -tax is currently set for 500baht per person
        """
        pay_post_tax = self.employee._apply_tax_deduction(Decimal('9500'))
        self.assertEqual(pay_post_tax, 9500)
    
    def test_net_pay(self):
        """
        Test whether the net pay is calculated property
        """
        net_pay = self.employee.calculate_net_pay(date(2014, 7, 1), date(2014, 7, 15))
        self.assertEqual(net_pay, 6150)
    
    
    
    
    
    
    
    