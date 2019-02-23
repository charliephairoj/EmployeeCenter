from decimal import Decimal
import dateutil.parser

from django.db import models
from administrator.models import User, Company
from contacts.models import Contact


class Account(models.Model):
    id = models.TextField(primary_key=True, unique=True)
    account_code = models.TextField(db_column='code')
    name = models.TextField(db_column='name_en')
    name_th = models.TextField(null=True)
    type = models.TextField(db_column="account_type", null=True)
    company = models.ForeignKey(Company, related_name="chart_of_accounts")
    
# Create your models here.
class Transaction(models.Model):
    account = models.ForeignKey(Account)
    debit = models.DecimalField(decimal_places=2, max_digits=12)
    credit = models.DecimalField(decimal_places=2, max_digits=12)
    balance = models.DecimalField(decimal_places=2, max_digits=12)
    transaction_id = models.TextField()
    description = models.TextField()
    transaction_date = models.DateTimeField()

    class Meta:
        permissions = (('can_view_transactions', 'Can View Transactions'),)


