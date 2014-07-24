from django.db import models

from contacts.models import Customer

# Create your models here.
class Shipment(models.Model):
    id = models.TextField(primary_key=True)
    customer = models.ForeignKey(Customer)


class Item(models.Model):
    description = model.TextField()
    width = models.DecimalField()
    depth = models.DecimalField()
    height = models.DecimalField(null=True)
    weight = models.DecimalFiel(default=0)