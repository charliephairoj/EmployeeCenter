#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from django.utils import timezone as tz
from rest_framework import serializers

from administrator.models import Company
from administrator.serializers import CompanyDefault, UserFieldSerializer, BaseLogSerializer
from acknowledgements.models import File, Acknowledgement, Item, Log as AckLog
from media.models import S3Object


logger = logging.getLogger(__name__)


"""
Internal Serializers
"""
class DefaultAcknowledgement(object):
    def set_context(self, serializer_field):
        self.acknowledgement = serializer_field.context['acknowledgement']

    def __call__(self):
        return self.acknowledgement

class AcknowledgementLogSerializer(BaseLogSerializer):
    acknowledgement = serializers.HiddenField(default=serializers.CreateOnlyDefault(DefaultAcknowledgement))
    type = serializers.CharField(default=serializers.CreateOnlyDefault('SALES ORDER'))

    class Meta:
        model = AckLog
        depth = 1
        fields = ('message', 'timestamp', 'employee', 'company', 'type', 'acknowledgement')

"""
Utility Services
"""
def log(message, acknowledgement, request):
    serializer = AcknowledgementLogSerializer(data={'message': message}, 
                                              context={'acknowledgement': acknowledgement,
                                                       'request': request})

    if serializer.is_valid(raise_exception=True):
        serializer.save()


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


        

