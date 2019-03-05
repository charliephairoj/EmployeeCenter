#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from contacts.models import Customer
from administrator.models import User
from accounting.account import service as account_service

logger = logging.getLogger(__name__)


def create(user=None, **kwargs):
    # Check that the user is a user instance
    assert isinstance(user, User), u"{0} should be a User instance".format(user)
    
    if "is_customer" in kwargs:
        kwargs.pop('is_customer')
        
    customer = Customer.objects.create(is_customer=True, **kwargs)

    try:
        customer.sync_google_contacts(user)
    except Exception as e:
        logger.warn(e)

    # Create AR for this customer
    account_service.create_account_receivable(user.company, customer)
    # Create AP for this customer
    account_service.create_account_payable(user.company, customer)
    
    return customer

def update(customer, data, user):
    """
    Update Service 
    """
    # Check customer is a customer instance
    assert isinstance(customer, Customer), u"{0} should be a Customer instance".format(customer)
    
    # Check that the user is a user instance
    assert isinstance(user, User), u"{0} should be a User instance".format(user)

    for field in validated_data.keys():
        setattr(customer, field, validated_data[field])

    customer.save()    

    try:
        customer.sync_google_contacts(self.context['request'].user)
    except Exception as e:
        logger.warn(e)

    return customer
