#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from administrator.models import User, Company
from contacts.models import Contact
from accounting.models import Account


logger = logging.getLogger(__name__)


def create_account_receivable(company, contact):
    # Check that the company is a Company instance
    assert isinstance(company, Company), u"{0} should be a Company instance".format(company)

    # Check customer is a customer instance
    assert isinstance(contact, Contact), u"{0} should be a sub class of Contact instance".format(contact)

    last_account = Account.objects.filter(company=company, account_code__startswith='12').order_by('-id').values('account_code').first() or '12000'

    new_account_code = int(last_account) + 1
    new_ar = Account.objects.create(name=u'Account Receivable: {0}'.format(contact.name),
                                    account_code=new_account_code,
                                    company=company)

    return new_ar


def create_account_payable(company, contact):
    # Check that the company is a Company instance
    assert isinstance(company, Company), u"{0} should be a Company instance".format(company)

    # Check customer is a customer instance
    assert isinstance(contact, Contact), u"{0} should be a sub class of Contact instance".format(contact)

    last_account = Account.objects.filter(company=company, account_code__startswith='22').order_by('-id').values('account_code').first() or '22000'

    new_account_code = int(last_account) + 1
    new_ap = Account.objects.create(name=u'Account Payable: {0}'.format(contact.name),
                                    account_code=new_account_code,
                                    company=company)

    return new_ap