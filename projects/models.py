"""
Project Models
"""
import datetime
import dateutil

from django.db import models
#from acknowledgements.models import Acknowledgement, Item as AcknowledgementItem
from products.models import Product, Model, Upholstery
from contacts.models import Customer
from supplies.models import Supply
from media.models import S3Object


class Project(models.Model):
    customer = models.ForeignKey(Customer, null=True)
    type = models.TextField(null=True)
    reference = models.TextField(null=True)
    codename = models.TextField(null=True)
    due_date = models.DateField(db_column="due_date", null=True)
    status = models.TextField(default="Planning")
    deleted = models.BooleanField(default=False)
    #supplies = models.ManyToManyField(Supply, through='ProjectSupply', related_name='supplies')
    files = models.ManyToManyField(S3Object, through='File', related_name='project')
    quantity = models.IntegerField(default=0)
    
    """
    @property
    def due_date(self):
        return self._due_date

    @due_date.setter
    def due_date(self, date):
        if isinstance(date, datetime.datetime):
            self._due_date = date.date()
        elif isinstance(date, datetime.date):
            self._due_date = date
        else:
            self._due_date = dateutil.parser.parse(date).date()
    """
    
    @classmethod
    def create(cls, **kwargs):
        """
        Creates a project and assigns
        the relevant attributes passed into the function.
        Raises an error if required data is missing
        """
        project = cls()

        #Required Attributes
        try:
            project.customer = Customer.objects.get(pk=kwargs["customer"]["id"])
        except KeyError:
            raise ValueError("Missing customer ID.")
        except Customer.DoesNotExist:
            raise ValueError("Customer does not exist.")
        try:
            project.type = kwargs["type"]
        except KeyError:
            raise ValueError("Missing project type")
        try:
            project.due_date = kwargs["due_date"]
        except KeyError:
            raise ValueError("Missing due date.")

        #Optional attributes
        if "reference" in kwargs:
            project.reference = kwargs["reference"]
        if "codename" in kwargs:
            project.codename = kwargs["codename"]

        project.save()
        return project


class Phase(models.Model):
    description = models.TextField()
    quantity = models.IntegerField(default=1)
    project = models.ForeignKey(Project, related_name="phases")
    due_date = models.DateTimeField(null=True)
    
    
class Room(models.Model):
    description = models.TextField()
    project = models.ForeignKey(Project, related_name="rooms")
    reference = models.TextField()
    image = models.ForeignKey(S3Object, null=True, related_name="+")
    schematic = models.ForeignKey(S3Object, null=True, related_name="+")
    status = models.TextField(default="Planning")
    deleted = models.BooleanField(default=False)
    files = models.ManyToManyField(S3Object, through='File', related_name='room')
    
    @classmethod
    def create(cls, **kwargs):
        """
        Creates and returns a new room
        """
        room = cls()
        #Required attributes
        try:
            room.project = Project.objects.get(pk=kwargs["project"]["id"])
        except KeyError:
            raise ValueError("Missing project ID.")
        except Project.DoesNotExist:
            raise ValueError("Project not found.")
        try:
            room.description = kwargs["description"]
        except KeyError:
            raise ValueError("Missing room description.")
        try:
            room.reference = kwargs["reference"]
        except KeyError:
            raise ValueError("Missing room reference")

        #Optional attributes
        if "image" in kwargs:
            try:
                print kwargs
                room.image = S3Object.objects.get(pk=kwargs["image"]["id"])
            except KeyError:
                raise ValueError("Missing image ID.")
        if "schematic" in kwargs:
            try:
                room.schematic = S3Object.objects.get(pk=kwargs["schematic"]["id"])
            except KeyError:
                raise ValueError("Missing schematic ID.")
        room.save()
        return room

    def update(self, **kwargs):
        """
        Updates the project
        """
        if "reference" in kwargs:
            self.reference = kwargs["reference"]
        if "status" in kwargs:
            self.status = kwargs["status"]

    def to_dict(self, user=None):
        """
        Returns the rooms attributes as a dictionary
        """
        data = {"id": self.id,
                "project": {'id': self.project.id,
                            'type': self.project.type,
                            'reference': self.project.reference,
                            'codename': self.project.codename,
                            'due_date': self.project.due_date.isoformat()},
                "reference": self.reference,
                "description": self.description,
                "status": self.status,
                "deleted": self.deleted,
                'items': [item.to_dict() for item in self.item_set.all()]}
        """
        if self.image:
            data["image"] = {"id": self.image.id,
                             "url": self.image.generate_url()},
        if self.schematic:
            data["schematic"] = {"id": self.schematic.id,
                                 "url": self.image.generate_url()}
        """
        return data


class Item(models.Model):
    due_date = models.DateField(db_column='due_date', null=True)
    delivery_date = models.DateField(db_column='delivery_date', null=True)
    room = models.ForeignKey(Room, related_name='items')
    status = models.TextField(default="Planning")
    description = models.TextField()
    reference = models.TextField(null=True)
    type = models.TextField(null=True)
    quantity = models.IntegerField(default=1)
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)
    #files = models.ManyToManyField(S3Object, through='File', related_name='room_item')
    supplies = models.ManyToManyField(Supply, through='ItemSupply', related_name='room_item')
    files = models.ManyToManyField(S3Object, through='File', related_name='room_item')
    
    

class File(models.Model):
    room = models.ForeignKey(Room, null=True)
    file = models.ForeignKey(S3Object, related_name="project_files")
    project = models.ForeignKey(Project, null=True)
    item = models.ForeignKey(Item, null=True)
    

class ProjectSupply(models.Model):
    supply = models.ForeignKey(Supply)
    project = models.ForeignKey(Project)
    quantity = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    
    
class ItemSupply(models.Model):
    supply = models.ForeignKey(Supply)
    item = models.ForeignKey(Item)
    quantity = models.DecimalField(decimal_places=10, max_digits=24, default=0)
    
    
    
    
    
    

