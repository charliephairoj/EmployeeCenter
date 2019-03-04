#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
import pprint

from .. import BaseProvider
from ..address import Provider as AddressProvider

from contacts.serializers import AddressSerializer, ContactSerializer

pp = pprint.PrettyPrinter()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ContactProvider(AddressProvider):

    class Meta:
        serializer = ContactSerializer

    def email(self):
        return self.generator.free_email()

    def telephone(self):
        return self.generator.phone_number()
        
    def addresses(self):
        logger.debug(pp.pformat(dir(self)))
        addrs = []
        addr = {}
        addr_ser = AddressSerializer()
        for f in addr_ser.get_fields():
            addr[f] = getattr(self, f)()

        addrs.append(addr)
        return addrs
    

