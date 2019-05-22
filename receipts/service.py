#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from decimal import getcontext

from receipts.models import File, Receipt, Item
from media.models import S3Object
from accounting.models import Account, Transaction, JournalEntry, Journal
from accounting.serializers import JournalEntrySerializer
from accounting.account import service as account_service


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


"""
Receipt Item Section
"""

def get_item(pk=None, id=None):
    return Item.objects.get(pk=pk or id)
    

"""
Receipt File Section
"""

def add_file(receipt=None, media_obj=None):

    assert isinstance(receipt, Receipt), "An receipt instance is required"
    assert isinstance(media_obj, S3Object), "A S3Object instance is required"

    File.objects.create(file=media_obj,
                        receipt=receipt)

def create_journal_entry(receipt, deposit_to):

    data = {
        'description': u'Received payment from {0} for invoice {1}'.format(receipt.customer.name, 
                                                                           receipt.invoice.id),
        'journal': {
            'id': Journal.objects.get(name_en='Assets').id
        },
        'transactions': []
    }

    # Add to Receivable
    receivable_tr_data = {
        'account': {
            'id': account_service.get(name='Accounts Receivable (A/R)').id
        },
        'credit': receipt.grand_total,
        'debit': None,
        'description': u'Recieved payment from {1} for Invoice {0}'.format(receipt.id, receipt.customer.name)
    }    

    data['transactions'].append(receivable_tr_data)

    # Add to assets
    asset_tr_data = {
        'account': {
            'id': deposit_to.id
        },
        'debit': receipt.grand_total,
        'credit': None,
        'description': u'Received payment from {1} for Invoice {0}'.format(receipt.invoice.id, receipt.customer.name)
    }    

    data['transactions'].append(asset_tr_data)


    serializer = JournalEntrySerializer(data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        



        

