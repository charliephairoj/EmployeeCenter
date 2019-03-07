#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from administrator.models import User
from contacts.models import Supplier
from accounting.account import service as account_service
from supplies.models import Supply, Product


logger = logging.getLogger(__name__)


"""
Supply Section
"""
def get(id=None, pk=None):
    return Supply.objects.get(pk=id or pk)

def get_by_description(description=None):
    """
    Get a Supply via description and supplier via Product
    """
    return Supply.objects.get(description=description)

def get_by_description_and_supplier(description=None, supplier=None):
    """
    Get a Supply via description and supplier via Product
    """
    product = Product.objects.get(supply__description=description,
                                  supplier=supplier)

    return product.supply

def create(employee=None, **kwargs):
    # Check that the user is a user instance
    assert isinstance(employee, User), u"{0} should be a User instance".format(employee)
    
    supply = Supply.objects.create(**kwargs)
    
    return supply

def create_supply_and_product(employee=None, supplier=None, unit_cost=0, **kwargs):

    supply = create(employee=employee, description=kwargs['description'])

    create_product(supply=supply, supplier=supplier, cost=unit_cost)

    return supply

def update(po, data, user):
    """
    Update Service 
    """
    # Check po is a po instance
    assert isinstance(po, PurchaseOrder), u"{0} should be a PurchaseOrder instance".format(po)
    
    # Check that the user is a user instance
    assert isinstance(user, User), u"{0} should be a User instance".format(user)

    for field in validated_data.keys():
        setattr(po, field, validated_data[field])

    po.save()    

    return po


"""
Product Section
"""
def create_product(supply=None, supplier=None, **kwargs):
    # Check supply is a Supply instance
    assert isinstance(supply, Supply), u"{0} should be a PurchaseOrder instance".format(supply)
    
    # Check that the supplier is a Supplier instance
    assert isinstance(supplier, Supplier), u"{0} should be a Supplier instance".format(supplier)   

    return Product.objects.create(supply=supply, 
                                  supplier=supplier,
                                  **kwargs) 
