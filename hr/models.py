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
        pass
        
        
class Attendance(models.Model):
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    employee = models.ForeignKey(Employee)
    regular_time = models.DecimalField()
    overtime = models.DecimalField(default=0)
    total_time = models.DecimalField()
    
    
