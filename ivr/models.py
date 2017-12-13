from __future__ import unicode_literals

from django.db import models
from administrator.models import User

# Create your models here

class Call(models.Model):
    twilio_id = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    type = models.TextField()
    incoming_number = models.TextField()
    forwarding_number = models.TextField(null=True)
    employee = models.ForeignKey(User, related_name='calls', null=True)
    recording_url = models.TextField()
    duration = models.IntegerField()


