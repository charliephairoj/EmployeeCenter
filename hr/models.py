from django.db import models

# Create your models here.
class Employee(models.Model):
    
    name = models.TextField()
    legal = models.BooleanField(default=True)
    department = models.TextField()
    telephone = models.TextField(null=True)
    wage = models.DecimalField()
    pay_period = models.TextField()
    employement_date = models.DateField(null=True)
    social_security_id = models.TextField(null=True)
    
    def calculate_net_pay(self):
        """
        Calculates the total amount owed to the employee
        after wages and deductions
        """
        if self.pay_period.lower() == 'monthly':
            return wage
            
        elif self.pay_period.lower() == 'daily':
            return 0
            
    def log_attendance(self, start_time, end_time):
        """
        Creates a instance of the attendance class to track
        employee attendance
        
        Takes the arguments of start time and end time, and creates
        a new instance. Attendance instance will automatically calculate
        regular_time, overtime, and total_time.
        """
        
    def _calculate_daily_wages_for_pay_period(self, start_time, end_time):
        attendances = Attendance.objects.filter(start_time__gte=start_time,
                                                end_time__lte=end_time,
                                                employee=self)
        total_regular_time = [a.regular_time for a in attendances]
        total_overtime = [a.overtime for a in attendances]
class Attendance(models.Model):
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    employee = models.ForeignKey(Employee)
    regular_time = models.DecimalField()
    overtime = models.DecimalField(default=0)
    total_time = models.DecimalField()
    
    def __init__(self, *args, **kwargs):
        """
        Override the initialization method
        """
        super(Attenance, self).__init(*args, **kwargs)
        
    def _calculate_different_time_types(self):
        """
        Calculates the times to be work"""
        self.total_time = (end_time - start_time).total_seconds() / 3600
        
        self.regular_time = 8 if self.total_time <= 8 else self.total_time
        
        self.overtime = self.total_time - self.regular_time if self.total_time <= 8 else 0
        
     