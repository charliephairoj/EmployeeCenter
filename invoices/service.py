#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from invoices.models import File, Invoice, Item
from media.models import S3Object


logger = logging.getLogger(__name__)


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


        

