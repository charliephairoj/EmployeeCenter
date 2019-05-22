#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from administrator.models import User, Company
from accounting.models import Account, Journal, JournalEntry


logger = logging.getLogger(__name__)


def create(journal=None, description=None, date=None):

    assert isinstance(journal, Journal), "Must be a Journal instance"

    je = JournalEntry(journal=journal, 
                      description=description)

    if date:
        je.date = date

    je.save()

    return je

