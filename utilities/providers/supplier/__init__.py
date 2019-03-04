#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging

from contacts.serializers import SupplierSerializer
from ..contact import ContactProvider

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Provider(ContactProvider):
   
    __provider__ = 'supplier'

    class Meta:
        serializer = SupplierSerializer()
    
    def is_supplier(self):
        return True

    def is_customer(self):
        return False

    def supplier(self):
        data = {}

        for f in self.Meta.serializer.get_fields():
            data[f] = getattr(self, f)()
           

        return data