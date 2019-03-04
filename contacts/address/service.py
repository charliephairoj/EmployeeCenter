#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from contacts.models import Address, Contact


logger = logging.getLogger(__name__)


def get(address_id=None):
    assert address_id

    return Address.objects.get(pk=address_id)

def create(contact, data):
    """
    Create Address
    """
    # Check customer is a customer instance
    assert isinstance(contact, Contact), u"{0} should be a sub class of Contact instance".format(contact)

    # Create the address instance
    return Address.objects.create(contact=contact, **data)

def update(address, data):
    """
    Update Address 
    """
    _validate_address_instance(address)
    
    for field in data.keys():
        setattr(address, field, data[field])
    
    address.save()

    return address

def delete(address):
    """
    Delete Address 
    """
    _validate_address_instance(address)

    address.delete()

def _validate_address_instance(address):
    # Check address is a address instance
    assert isinstance(address, Address), u"{0} should be a Address instance".format(address)
