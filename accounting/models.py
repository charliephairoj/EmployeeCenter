from decimal import Decimal
import dateutil.parser

from django.db import models
from django.contrib.auth.models import User
from contacts.models import Contact


# Create your models here.
class Transaction(models.Model):
    contact = models.ForeignKey(Contact)
    amount = models.DecimalField(decimal_places=2, max_digits=12)
    currency = models.CharField(max_length=3)
    type = models.CharField(max_length=10)
    invoice_id = models.TextField()
    vendor = models.TextField()
    comments = models.TextField()
    employee = models.ForeignKey(User)
    transaction_date = models.DateTimeField()

    class Meta:
        permissions = (('can_view_transactions', 'Can View Transactions'),)

    def get_data(self, **kwargs):
        return {'id': self.id,
                'name': self.contact.name,
                'amount': str(self.amount),
                'currency': self.currency,
                'type': self.type,
                'invoice': {'id': self.invoice_id},
                'vendor': self.vendor,
                'comments': self.comments,
                'employee': self.employee.first_name + ' ' + self.employee.last_name,
                'transaction_date': self.transaction_date.isoformat()}

    def set_data(self, data, **kwargs):
        print data
        try:
            self.contact = Contact.objects.get(id=data["contact"]["id"])
        except KeyError:
            print "no contact"
        if "name" in data:
            self.name = data["name"]
        if "amount" in data:
            self.amount = Decimal(str(data["amount"]))
        if "currency" in data:
            self.currency = data["currency"]
        if "type" in data:
            self.type = data["type"]
        if "invoice" in data:
            if "id" in data["invoice"]:
                self.invoice_id = data["invoice"]["id"]
        if "vendor" in data:
            self.vendor = data["vendor"]
        if "comments" in data:
            self.comments = data["comments"]
        if "user" in kwargs:
            self.employee = kwargs["user"]
        if "transaction_date" in data:
            self.transaction_date = dateutil.parser.parse(data["transaction_date"])

