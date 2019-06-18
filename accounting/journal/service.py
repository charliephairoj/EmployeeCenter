#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from administrator.models import User, Company
from contacts.models import Contact
from accounting.models import Journal


logger = logging.getLogger(__name__)


def get(name=None, pk=None, company=None):
    
    assert isinstance(company, Company), "An company instance is required"
    assert not (name is None and pk is None), "Must provide Journal name or id"

    filtered_journals = Journal.objects.filter(company=company)

    if name:
        return filtered_journals.get(name_en=name)

    if pk:
        return filtered_journals.get(pk=pk)

