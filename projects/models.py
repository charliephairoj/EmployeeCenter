"""
Project Models
"""
import datetime
import dateutil

from django.db import models
from acknowledgements.models import Acknowledgement, Item as AcknowledgementItem
from products.models import Product, Model, Upholstery
from contacts.models import Customer
from auth.models import S3Object


class Project(models.Model):
    customer = models.ForeignKey(Customer)
    type = models.TextField()
    reference = models.TextField()
    codename = models.TextField()
    _due_date = models.DateField(db_column="due_date")
    status = models.TextField(default="Planning")

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

    @classmethod
    def create(cls, **kwargs):
        project = cls()
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
            project.reference = kwargs["reference"]
        except KeyError:
            raise ValueError("Missing project reference.")
        try:
            project.codename = kwargs["codename"]
        except KeyError:
            raise ValueError("Missing project codename.")
        try:
            project.due_date = kwargs["due_date"]
        except KeyError:
            raise ValueError("Missing due date.")

        project.save()
        return project

    def update(self, **kwargs):
        """
        Updates the Project
        """
        if "due_date" in kwargs:
            self.due_date = kwargs["due_date"]
        if "status" in kwargs:
            self.status = kwargs["status"]
        if "reference" in kwargs:
            if kwargs["reference"] != self.reference:
                self._update_reference(kwargs["reference"])

    def to_dict(self, user=None):
        """
        Returns the projects attribute as a dictionary
        """
        return {"id": self.id,
                'customer': self.customer.to_dict(),
                "reference": self.reference,
                "codename": self.codename,
                "due_date": self.due_date.isoformat(),
                "status": self.status,
                "type": self.type,
                "rooms": [room.to_dict() for room in self.room_set.all()]}

    def _update_reference(self, new_reference):
        """
        Updates the reference

        This method will update the reference, along with the corresponding
        model and all the items in this project
        """
        old_reference = self.reference
        self.reference = new_reference

        try:
            model = Model.objects.get(model=old_reference)
            model.model = self.reference
        except Model.DoesNotExist:
            pass

        items = [room.item_set.all() for room in self.room_set.all()]
        for item in items:
            if item.type.lower() == "upholstery":
                description = "{0} {1}".format(item.model.model, item.configuration.configuration)
                item.update(description=description)


class Room(models.Model):
    description = models.TextField()
    project = models.ForeignKey(Project)
    reference = models.TextField()
    image = models.ForeignKey(S3Object, null=True, related_name="+")
    schematic = models.ForeignKey(S3Object, null=True, related_name="+")
    status = models.TextField(default="Planning")

    @classmethod
    def create(cls, **kwargs):
        """
        Creates and returns a new room
        """
        room = cls()
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
        
        if "image" in kwargs:
            try:
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
    _due_date = models.DateField(db_column='due_date')
    _delivery_date = models.DateField(db_column='delivery_date', null=True)
    room = models.ForeignKey(Room)
    status = models.TextField(default="Planning")
    description = models.TextField()
    reference = models.TextField()
    image = models.ForeignKey(S3Object, null=True, related_name="+")
    schematic = models.ForeignKey(S3Object, db_column="schematic_id", null=True, related_name="+")
    #schematic_last_modified = models.DateTimeField()
    type = models.TextField()
    product = models.ForeignKey(Product, null=True, related_name="+")
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)

    """
    @property
    def schematic(self):
        return {'url': self._schematic.generate_url(),
                'last_modified': self.schematic_last_modified()}"""
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

    @property
    def delivery_date(self):
        return self._delivery_date

    @delivery_date.setter
    def delivery_date(self, date):
        if isinstance(date, datetime.datetime):
            self._delivery_date = date.date()
        elif isinstance(date, datetime.date):
            self._delivery_date = date
        else:
            self._delivery_date = dateutil.parser.parse(date).date()

    @classmethod
    def create(cls, user=None, **kwargs):
        """
        Creates and returns a new item
        """
        item = cls()

        try:
            item.room = Room.objects.get(pk=kwargs["room"]["id"])
        except KeyError:
            raise ValueError("Missing room ID")

        try:
            item.type = kwargs["type"]
        except:
            raise ValueError("Missing item type.")

        try:
            item.reference = kwargs["reference"]
        except:
            raise ValueError("Missing item reference")

        try:
            item.due_date = kwargs["due_date"]
        except KeyError:
            item.due_date = item.room.project.due_date
        try:
            item.delivery_date = kwargs["delivery_date"]
        except KeyError:
            item.delivery_date = item.due_date

        #Build custom product
        if item.type.lower() == "custom":
            if kwargs["product"]["type"].lower() == "upholstery":
                item.product = item._create_custom_upholstery(kwargs["product"])
                item.description = item.product.description

        #Add regular product
        elif item.type.lower() == "product":
            try:
                item.product = Product.objects.get(pk=kwargs["product"]["id"])
                item.description = item.product.description
            except KeyError:
                raise ValueError("Missing product ID")

        #Add build-in
        elif item.type.lower() == "build-in":
            try:
                item.description = kwargs["description"]
            except KeyError:
                raise ValueError("Missing build-in description")
        else:
            raise ValueError("Type must be 'Custom', 'Product', or 'Build-In'.")

        item.save()
        return item

    def update(self, **kwargs):
        """
        Updates the item
        """
        if "room" in kwargs:
            try:
                self.room = Room.objects.get(pk=kwargs["room"]["id"])
            except KeyError:
                raise ValueError("Missing room ID")

        if "due_date" in kwargs:
            self.due_date = kwargs["due_date"]
        if "delivery_date" in kwargs:
            self.delivery_date = kwargs["delivery_date"]
        if "product" in kwargs:
            if self.type.lower() == "custom":
                if "id" in kwargs["product"]:
                    if self.product.id != kwargs["product"]["id"]:
                        raise TypeError("Unable to change product for a custom item.")
                self.product.update(**kwargs["product"])
            elif self.type.lower() == "product":
                self.product.update(**kwargs["product"])

        if "schematic" in kwargs:
            try:
                if kwargs["schematic"]["id"] != self.schematic.id:
                    old_schematic = self.schematic
                    self.schematic = S3Object.objects.get(pk=kwargs["schematic"]["id"])
                    old_schematic.delete()
                    if self.type.lower() == "custom":
                        self.product.update(schematic=kwargs["schematic"])
            except KeyError:
                raise ValueError("Missing schematic ID.")
            except S3Object.DoesNotExist:
                raise ValueError("Schematic not found.")

        if "image" in kwargs:
            try:
                if kwargs["image"]["id"] != self.image.id:
                    old_img = self.image
                    self.image = S3Object.objects.get(pk=kwargs["image"]["id"])
                    old_img.delete()
                    if self.type.lower() == "custom":
                        self.product.update(image=kwargs["image"]["id"])

            except KeyError:
                raise ValueError("Missing image ID.")
            except S3Object.DoesNotExist:
                raise ValueError("Schematic not found")

    def to_dict(self, user=None):
        data = {"id": self.id,
                "reference": self.reference,
                "due_date": self.due_date.isoformat(),
                "delivery_date": self.delivery_date.isoformat(),
                "description": self.description,
                "type": self.type,
                "last_modified": self.last_modified.isoformat()}
        
        if self.image:
            data["image"] = {"id": self.image.id,
                             "url": self.image.generate_url()}
        if self.schematic:
            data["schematic"] = {"id": self.schematic.id,
                                 "url": self.schematic.generate_url()}
        if self.product:
            data["product"] = self.product.to_dict()
            
        return data
    
    def _create_custom_upholstery(self, product_data):
        """
        Creates a corresponding custom upholstery item
        """
        try:
            model = Model.objects.get(model=self.room.project.reference,
                                      name=self.room.project.codename)
        except Model.DoesNotExist:
            model = Model.create(model=self.room.project.reference,
                             name=self.room.project.codename,
                             collection="Dellarobbia Thailand")
            model.save()

        product_data["model"] = {"id": model.id}
        return Upholstery.create(**product_data)


