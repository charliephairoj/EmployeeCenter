#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging

from faker import Faker
from rest_framework import serializers

from contacts.serializers import SupplierSerializer


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BaseFixture(object):
    faker = Faker()

    def __init__(self, *args, **kwargs):
        super(BaseFixture, self).__init__(*args, **kwargs)
        self.faker.seed(234234)
        self._serializer_fields = self.Meta.serializer.get_fields()

    def populate(self, fields=None):

        data = {}
        
        if fields is None:
            fields = self._serializer_fields

        for f_name in fields:
            # Get field instance
            field = fields[f_name]

            if issubclass(field.__class__, serializers.ListSerializer):
                logger.debug(field.__dict__)
            elif issubclass(field.__class__, serializers.ModelSerializer):
                sub_fields = field.get_fields()
                data[f_name] = self.populate(sub_fields)
            else:
                data[f_name] = getattr(self.faker, f_name)()


        return data


class SupplierFixture(BaseFixture):

    class Meta:
        serializer = SupplierSerializer()

    






