#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from acknowledgements.models import File, Acknowledgement, Item
from media.models import S3Object


logger = logging.getLogger(__name__)


"""
Acknowledgement Item Section
"""

def get_item(pk=None, id=None):
    return Item.objects.get(pk=pk or id)
    

"""
Acknowledgement File Section
"""

def add_file(acknowledgement=None, media_obj=None):

    assert isinstance(acknowledgement, Acknowledgement), "An acknowledgement instance is required"
    assert isinstance(media_obj, S3Object), "A S3Object instance is required"

    File.objects.create(file=media_obj,
                        acknowledgement=acknowledgement)


        

