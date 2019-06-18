#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from decimal import getcontext

from invoices.models import File, Invoice, Item
from media.models import S3Object
from accounting.models import Account, Transaction, JournalEntry, Journal
from accounting.serializers import JournalEntrySerializer
from accounting.account import service as account_service


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


"""
Invoice Item Section
"""

def get_item(pk=None, id=None):
    return Item.objects.get(pk=pk or id)
    

"""
Invoice File Section
"""

def add_file(invoice=None, media_obj=None):

    assert isinstance(invoice, Invoice), "An invoice instance is required"
    assert isinstance(media_obj, S3Object), "A S3Object instance is required"

    File.objects.create(file=media_obj,
                        invoice=invoice)

def create_journal_entry(invoice):

    data = {
        'description': u'Invoice {0}'.format(invoice.id),
        'journal': {
            'id': Journal.objects.get(name_en='Revenue').id
        },
        'transactions': []
    }

    # Add to Receivable
    payable_tr_data = {
        'account': {
            'id': account_service.get(name='Accounts Receivable (A/R)').id
        },
        'debit': invoice.grand_total,
        'credit': None,
        'description': u'Invoice {0}: {1}'.format(invoice.id, invoice.customer.name)
    }    

    data['transactions'].append(payable_tr_data)

    # Add Sales VAT
    if invoice.vat_amount > 0:
        vat_tr_data = {
            'account': {
                'id': account_service.get(name='VAT Payable').id
            },
            'credit': invoice.vat_amount,
            'debit': None,
            'description': u'Invoice {0}: {1}'.format(invoice.id, invoice.customer.name)
        }  
        data['transactions'].append(vat_tr_data)


    #Add Transactions for income for each item
    for item in invoice.items.all():
        income_tr_data = {
            'account': {
                'id': account_service.get(name='Sales of Product Income').id
            },
            'credit': item.total,
            'debit': None,
            'description': u'Invoice {0}: {1}'.format(invoice.id, item.description)
        }
        data['transactions'].append(income_tr_data)

    logger.debug(data)

    serializer = JournalEntrySerializer(data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()

        invoice.journal_entry = serializer.instance
        invoice.save()
        



        

