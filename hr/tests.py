"""
Testing File for HR application
"""
import logging
import unittest
from decimal import Decimal
from datetime import date, datetime, time

from django.test import TestCase
from tastypie.test import ResourceTestCase
from pytz import timezone

from hr.models import Employee, Attendance, Shift


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
    'social_security_id': '123-33-333'
}

employee2_data = {
    'name': 'test2',
    'legal': True,
    'department': 'painting',
    'telephone': '0983337654',
    'wage': '550',
    'pay_period': 'Daily',
    'employement_date': date.today(),
    'social_security_id': '123-33-333'
}

employee3_data = {
    'name': 'test3',
    'legal': False,
    'department': 'carpentry',
    'telephone': '0834679880',
    'wage': '300',
    'pay_period': 'Daily',
    'employement_date': date.today(),
    'social_security_id': '123-33-333'
}


class AttendanceTest(ResourceTestCase):
    """
    Testing class for attendance
    """
    def setUp(self):
        """
        Set up the Testing clas:
        """
        super(AttendanceTest, self).setUp()
        
        self.api_client.client.login(username='test', password='test')
        
        self.shift = Shift(start_time=time(8, 0),
                           end_time=time(17, 0))
        self.shift.save()
        self.employee = Employee(shift=self.shift, **employee2_data)
        self.employee.save()
        
        self.attendance = Attendance(date=date(2014, 7, 1),
                                     start_time=datetime(2014, 7, 1, 7, 30, 0, tzinfo=timezone('Asia/Bangkok')),
                                     end_time=datetime(2014, 7, 1, 17, 15, 0, tzinfo=timezone('Asia/Bangkok')), 
                                     employee=self.employee)
        self.attendance.save()
        
    def test_accessing_attendance_instance(self):
        """
        Tests that the attendance data can be correctly accessed by the model
        """
        a = Attendance.objects.get(pk=1)
        self.assertEqual(a.start_time, datetime(2014, 7, 1, 7, 30, 0, tzinfo=timezone('Asia/Bangkok')))
        self.assertEqual(a.end_time, datetime(2014, 7, 1, 17, 15, 0, tzinfo=timezone('Asia/Bangkok')))
        
    def test_processing_times_based_on_instance_shift_with_normal_times(self):
        """
        Tests that the instance can correctly assign the time
        based on what shift the instance
        """
        a = Attendance(date=date(2014, 7, 2))
        a.employee = self.employee
        a.shift = self.shift
        a.save()
        
        self.assertIsNone(a.start_time)
        self.assertIsNone(a.end_time)
        
        d = datetime(2014, 7, 2, 7, 45, 0, tzinfo=timezone('Asia/Bangkok'))
        a.assign_datetime(d)
        self.assertIsNotNone(a.start_time)
        self.assertEqual(a.start_time, d)
        self.assertIsNone(a.end_time)
        
        d = datetime(2014, 7, 2, 18, 27, 0, tzinfo=timezone('Asia/Bangkok'))
        a.assign_datetime(d)
        self.assertIsNotNone(a.end_time)
        self.assertEqual(a.end_time, d)
        self.assertIsNotNone(a.start_time)
        
    def test_processing_times_based_on_instance_shift_with_late_times(self):
        """
        Tests that the instance can correctly assign the time
        based on what shift the instance
        """
        a = Attendance(date=date(2014, 7, 2))
        a.employee = self.employee
        a.shift = self.shift
        a.save()
        
        self.assertIsNone(a.start_time)
        self.assertIsNone(a.end_time)
        
        d = datetime(2014, 7, 2, 8, 45, 0, tzinfo=timezone('Asia/Bangkok'))
        a.assign_datetime(d)
        self.assertIsNotNone(a.start_time)
        self.assertEqual(a.start_time, d)
        self.assertIsNone(a.end_time)
        
        d = datetime(2014, 7, 2, 10, 45, 0, tzinfo=timezone('Asia/Bangkok'))
        a.assign_datetime(d)
        self.assertIsNotNone(a.start_time)
        self.assertEqual(a.start_time, d)
        self.assertIsNone(a.end_time)
        
        d = datetime(2014, 7, 2, 16, 45, 0, tzinfo=timezone('Asia/Bangkok'))
        a.assign_datetime(d)
        self.assertIsNotNone(a.start_time)
        self.assertIsNotNone(a.end_time)
        self.assertEqual(a.end_time, d)
        
    def test_calculate_overtime_function(self):
        """
        Tests 'calculate overtime'
        """
        self.attendance.regular_time = 8
        self.attendance.total_time = 8.4
        self.assertNotEqual(self.attendance.overtime, 8)
        
        self.attendance._calculate_overtime()
        self.assertEqual(self.attendance.overtime, 0)
        
        self.attendance.regular_time = 8
        self.attendance.total_time = 9.4
        self.assertNotEqual(self.attendance.overtime, 1)
        
        self.attendance._calculate_overtime()
        self.assertEqual(self.attendance.overtime, 1)
        
        self.attendance.regular_time = 8
        self.attendance.total_time = 10.6
        self.assertNotEqual(self.attendance.overtime, 2.5)
        
        self.attendance._calculate_overtime()
        self.assertEqual(self.attendance.overtime, 2.5)
        
    def test_cutoff_times_without_ot(self):
        """
        Tests that the hours are cutoff 
        correctly even if the employee clocks in early
        or clocks out late
        """
        self.attendance._calculate_times()
        self.assertEqual(self.attendance.regular_time, 8)
        self.assertEqual(self.attendance.total_time, 8)
        self.assertEqual(self.attendance.overtime, 0)
    
    def test_times_with_overtime_but_not_over_minumum(self):
        """
        Tests that the times are correct if overtime is enabled for
        this particular date
        """
        self.attendance.enable_overtime = True
        self.attendance.save()
        
        self.assertEqual(self.attendance.regular_time, 8)
        self.assertEqual(self.attendance.total_time, 8.25)
        self.assertEqual(self.attendance.overtime, 0)
        
        a = Attendance(employee=self.employee,
                       date=date(2014, 7, 2),
                       start_time=datetime(2014, 7, 2, 8, 0, 0, tzinfo=timezone('Asia/Bangkok')),
                       end_time=datetime(2014, 7, 2, 17, 45, 0, tzinfo=timezone('Asia/Bangkok')))
        a.enable_overtime = True
        a.save()
        a._calculate_times()
        self.assertEqual(a.regular_time, 8)
        self.assertEqual(a.total_time, 8.75)
        self.assertEqual(a.overtime, 0)
        
    def test_times_with_overtime_but_not_over_minumum(self):
        """
        Tests that the times are correct if overtime is enabled for
        this particular date
        """
        a = Attendance(employee=self.employee,
                       date=date(2014, 7, 2),
                       start_time=datetime(2014, 7, 2, 8, 0, 0, tzinfo=timezone('Asia/Bangkok')),
                       end_time=datetime(2014, 7, 2, 18, 45, 0, tzinfo=timezone('Asia/Bangkok')))
        a.enable_overtime = True
        a.save()
        a._calculate_times()
        self.assertEqual(a.regular_time, 8)
        self.assertEqual(a.total_time, 9.75)
        self.assertEqual(a.overtime, 1.5)
    
    def test_get_list(self):
        """
        Test getting a list of objects
        """
        resp = self.api_client.get('/api/v1/attendance')
        self.assertHttpOK(resp)
        
        obj_list = self.deserialize(resp)
        
    def test_get_list_filter_by_employee(self):
        """
        Test getting a list of objects filtered by employee
        """
        resp = self.api_client.get('/api/v1/attendance?employee=1')
        self.assertHttpOK(resp)
        
    def test_get(self):
        """
        Tests basic get of single object
        """
        resp = self.api_client.get('/api/v1/attendance/1')
    
    
@unittest.skip("ok")
class Employee1Test(TestCase):
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
class Employee2Test(TestCase):
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
class Employee3Test(TestCase):
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
    
    
    
    
    
    
    
    