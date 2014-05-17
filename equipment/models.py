from django.db import models


class Equipment(models.Model):
    description = models.TextField()
    brand = models.TextField()
    status = models.TextField()
    cost = models.DecimalField(null=True)

