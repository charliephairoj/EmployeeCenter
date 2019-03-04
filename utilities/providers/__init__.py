#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
import pprint

from faker import Faker
from faker.providers import BaseProvider

pp = pprint.PrettyPrinter()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BaseProvider(BaseProvider):
    __provider__ = 'base'
    __lang__ = 'en_US'

    def id(self):
        return self.random_int()

    def _add_provider(self, provider):

        self.generator.add_provider(provider)

        for method_name in dir(provider):
                # skip 'private' method
                if method_name.startswith('_'):
                    continue

                faker_function = getattr(provider, method_name)

                if callable(faker_function):
                    # add all faker method to generator
                    setattr(self, method_name, faker_function)


class ProviderFactory(object):
    faker = Faker()

    
    class Meta:
        serializer = None

    def create(self, serializer):

        fields = serializer.get_fields()

        return self.populate(fields)

    def populate(self, fields):

        data = {}

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


    

