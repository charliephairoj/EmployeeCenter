#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from decimal import Decimal
from datetime import datetime

from administrator.models import User, Company
from accounting.models import Account, Journal, Transaction, JournalEntry


logger = logging.getLogger(__name__)


def create(journal_entry=None, account=None, debit=Decimal('0'), credit=Decimal('0'), transaction_date=None, description=None):

    assert isinstance(journal_entry, JournalEntry), "Must be a Journal Entry instance"
    assert isinstance(account, Account), "Must be a Account instance"

    logger.debug(debit)
    logger.debug(credit)

    t = Transaction(journal_entry=journal_entry, 
                    account=account,
                    description=description,
                    debit=debit,
                    credit=credit)

    if transaction_date:
        t.transaction_date = datetime.now()

    t.save()

    return t



