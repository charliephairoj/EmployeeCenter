from django.db import models

from hr.models import Employee
from media.models import S3Object

class Equipment(models.Model):
    description = models.TextField(null=True)
    brand = models.TextField(null=True)
    status = models.TextField(null=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    employee = models.ForeignKey(Employee, null=True, related_name="equipments")
    image = models.ForeignKey(S3Object, null=True)
