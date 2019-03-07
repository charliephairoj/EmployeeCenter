#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from administrator.models import User


logger = logging.getLogger(__name__)


"""
User Section
"""

def get(id=None, pk=None):

    if id is None and pk is None:
        raise ValueError(u'A valid id or pk is required')

    return User.objects.get(pk=id or pk)

def get_by_context(serializer, nested=False):
    """
    Get the current user by the DRF serializer context
    """

    try:
        return serializer.context['request'].user
    except KeyError as e:
        logger.warn(e)
        return serializer.parent.parent.context['request'].user
    

