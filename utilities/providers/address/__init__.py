#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging

from faker import Faker
from faker.providers.address import Provider as AProvider
from .. import BaseProvider


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Provider(AProvider, BaseProvider):
    def address1(self):
        return self.street_address()

    def territory(self):
        return self.city()

    def zipcode(self):
        return self.postcode()