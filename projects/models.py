from django.db import models
from acknowledgements.models import Acknowledgement, Item as AcknowledgementItem
from contacts.models import Customer
from


class Project(models.Model):
    customer = models.ForeignKey(Customer)
    type = models.TextField(default="House")
    _due_date = models.DateTimeField()

    @property
    def due_date(self):
        return self._due_date

    @due_date.setter(self, new_date):
        self._due_date = new_date


class Room(models.Model):
    description = models.TextField()
    project = models.ForeignKey(Project)


class Item():
    _due_date = models.DateTimeField(db_column='due_date')
    _delivery_date = models.DateTimeField(db_column='delivery_date')
    room = models.ForeignKey(Room)
    acknowledgement = models.ForeignKey(AcknowledgementItem)
    status = models.TextField()

    @property
    def due_date(self):
        return self._due_date

    @due_date.setter
    def due_date(self, new_date):
        self._due_date = new_date




