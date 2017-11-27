from decimal import Decimal
import dateutil.parser
import logging

from django.db import models
from django.contrib.auth.models import User
from contacts.models import Contact


logger = logging.getLogger(__name__)


class Journal(models.Model):
    name_en = models.TextField()
    name_th = models.TextField()


class JournalEntry(models.Model):
    description = models.TextField()
    date = models.DateField(auto_now=True)
    journal = models.ForeignKey(Journal)
    

class Account(models.Model):
    code = models.TextField(null=True)
    name_en = models.TextField(null=True)
    name_th = models.TextField(null=True)
    type = models.TextField(db_column="account_type", null=True)
    

class Transaction(models.Model):
    account = models.ForeignKey(Account)
    journal_entry = models.ForeignKey(JournalEntry)
    debit = models.DecimalField(decimal_places=2, max_digits=12)
    credit = models.DecimalField(decimal_places=2, max_digits=12)
    balance = models.DecimalField(decimal_places=2, max_digits=12)
    transaction_id = models.TextField()
    description = models.TextField()
    transaction_date = models.DateTimeField()

    class Meta:
        permissions = (('can_view_transactions', 'Can View Transactions'),)
