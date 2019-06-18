#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import csv

from administrator.models import User, Company
from accounting.models import Account


logger = logging.getLogger(__name__)


def create_default_accounts(company):
    with open('accounting/default-chart-of-accounts.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            try:
                Account.objects.get(name=row[0],
                                    type=row[1],
                                    type_detail=row[2],
                                    company=company)
            except Account.DoesNotExist as e:
                a = Account(name=row[0],
                            type=row[1],
                            type_detail=row[2],
                            company=company)
                a.save()


def get(name=None, pk=None, company=None):
    assert not company is None, "Must provide a valid company"
    assert not (name is None and pk is None), "Must provide Account name or id"

    filtered_accounts = Account.objects.filter(company=company)

    if name:
        return filtered_accounts.get(name=name)

    if pk:
        return filtered_accounts.get(pk=pk)


def create_account_receivable(company, contact):
   

    try:
        last_account = Account.objects.filter(company=company, account_code__startswith='12').order_by('-id').values('account_code').first()['account_code']
    except Exception as e:
        last_account = '12000'

    parent = get(name='Accounts Receivable (A/R)', company=company)
    new_account_code = int(last_account) + 1
    new_ar = Account.objects.create(name=u'Account Receivable: {0}'.format(contact.name),
                                    account_code=new_account_code,
                                    type=parent.type,
                                    type_detail=parent.type_detail,
                                    company=company,
                                    parent=parent)

    return new_ar


def create_account_payable(company, contact):
    try:
        last_account = Account.objects.filter(company=company, account_code__startswith='22').order_by('-id').values('account_code').first()['account_code']
    except Exception as e:
        last_account = '22000'

    parent = get(name='Accounts Payable (A/P)', company=company)
    new_account_code = int(last_account) + 1
    new_ap = Account.objects.create(name=u'Account Payable: {0}'.format(contact.name),
                                    account_code=new_account_code,
                                    type=parent.type,
                                    type_detail=parent.type_detail,
                                    company=company, 
                                    parent=parent)

    return new_ap