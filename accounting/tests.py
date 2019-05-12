"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError

from accounting.models import Journal, JournalEntry, Transaction, Account
from accounting.serializers import JournalEntrySerializer
from administrator.models import Company


logger = logging.getLogger(__name__)


class JournalEntryTest(APITestCase):

    def setUp(self):

        c = Company(name="Turkey Group Co., Ltd.")
        c.save()

        j = Journal(name='Revenue')
        j.save()

        setup_accounts = [
            {
                'name': 'Accounts Receivable (A/R)',
                'type': 'Current Assets'    
            },
            {
                'name': 'Cash',
                'type': 'Current Assets' 
            }
        ]

        for a in setup_accounts:
            Account(name=a['name'], type=a['type'], company=c).save()


    def test_creating_journal(self):

        data = {
            'description': u'Invoice {0}'.format(1),
            'journal': {
                'id': Journal.objects.get(name_en='Revenue').id
            },
            'transactions': []
        }

        # Add to Receivable
        withdrawal_data = {
            'account': {
                'id': Account.objects.get(name='Accounts Receivable (A/R)').id
            },
            'credit': Decimal('10600.00'),
            'debit': None,
            'description': u'Invoice {0}'.format(1)
        }    

        data['transactions'].append(withdrawal_data)

        # Add to Receivable
        deposit_data = {
            'account': {
                'id': Account.objects.get(name='Cash').id
            },
            'debit': Decimal('10600.00'),
            'credit': None,
            'description': u'Invoice {0}'.format(1)
        }    

        data['transactions'].append(deposit_data)

        serializer = JournalEntrySerializer(data=data)

        if serializer.is_valid(raise_exception=True):
            serializer.save()

        self.assertEqual(JournalEntry.objects.all().count(), 1)
        self.assertEqual(Transaction.objects.all().count(), 2)

    def test_failed_creating_journal(self):

        data = {
            'description': u'Invoice {0}'.format(1),
            'journal': {
                'id': Journal.objects.get(name_en='Revenue').id
            },
            'transactions': []
        }

        # Add to Receivable
        withdrawal_data = {
            'account': {
                'id': Account.objects.get(name='Accounts Receivable (A/R)').id
            },
            'credit': Decimal('10500.00'),
            'debit': None,
            'description': u'Invoice {0}'.format(1)
        }    

        data['transactions'].append(withdrawal_data)

        # Add to Receivable
        deposit_data = {
            'account': {
                'id': Account.objects.get(name='Cash').id
            },
            'debit': Decimal('10600.00'),
            'credit': None,
            'description': u'Invoice {0}'.format(1)
        }    

        data['transactions'].append(deposit_data)

        serializer = JournalEntrySerializer(data=data)

        self.assertRaises(ValidationError, serializer.is_valid, raise_exception=True)
        self.assertEqual(JournalEntry.objects.all().count(), 0)
        self.assertEqual(Transaction.objects.all().count(), 0)


        