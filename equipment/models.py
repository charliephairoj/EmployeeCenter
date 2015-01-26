from django.db import models


class Equipment(models.Model):
    description = models.TextField()
    brand = models.TextField()
    status = models.TextField()
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True)

