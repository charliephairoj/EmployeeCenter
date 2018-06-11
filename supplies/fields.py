#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging

from rest_framework import serializers


logger = logging.getLogger(__name__)


class SupplierField(serializers.Field):
    """
    Supplier based on if there is a supplier_id in the query params
    """
    def to_representation(self, obj):
        return None

    def to_internal_value(self, data):
        logger.debug(data)
        logger.debug(self.context)
        return None