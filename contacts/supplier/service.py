#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from contacts.models import Supplier
from administrator.models import User


logger = logging.getLogger(__name__)


def create(user=None, **kwargs):
    # Check that the user is a user instance
    assert isinstance(user, User), u"{0} should be a User instance".format(user)

    if "is_supplier" in kwargs:
        kwargs.pop('is_supplier')
        
    supplier = Supplier.objects.create(is_supplier=True, **kwargs)

    try:
        supplier.sync_google_contacts(user)
    except Exception as e:
        logger.warn(e)

    # Create AR for this supplier
    account_service.create_account_receivable(user.company, supplier)
    # Create AP for this supplier
    account_service.create_account_payable(user.company, supplier)

    return supplier

def update(supplier, data, user):
    """
    Update Service 
    """
    # Check supplier is a supplier instance
    assert isinstance(supplier, Supplier), u"{0} should be a Supplier instance".format(supplier)
    
    # Check that the user is a user instance
    assert isinstance(user, User), u"{0} should be a User instance".format(user)

    for field in validated_data.keys():
        setattr(supplier, field, validated_data[field])

    supplier.save()    

    try:
        supplier.sync_google_contacts(self.context['request'].user)
    except Exception as e:
        logger.warn(e)

    return supplier
