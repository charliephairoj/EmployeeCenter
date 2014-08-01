"""
Testing File for HR application
"""
import logging
import unittest
from decimal import Decimal
from datetime import date, datetime

from django.test import TestCase

from hr.models import Employee, Attendance


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
    
    
    
    
    
    
    
    