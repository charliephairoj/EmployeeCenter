#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging

from faker import Faker
from faker.providers.address import Provider as AddressProvider


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Provider(AddressProvider):
    def street1(self):
        return self.street_name()
