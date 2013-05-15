from django.db import models
from acknowledgements.models import Acknowledgement
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
    project = models.ForeignKey(Project)


class Item():
    room = models.ForeignKey(Room)
    acknowledgement = models.ForeignKey(Acknowledgement)


