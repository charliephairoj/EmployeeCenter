#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from decimal import Decimal
from pytz import timezone

import boto
from rest_framework import serializers
from rest_framework.fields import DictField
from django.contrib.auth.models import User

from deals.models import Deal
from contacts.models import Contact, Customer
from acknowledgements.models import Acknowledgement
from estimates.models import Estimate
from estimates.serializers import EstimateSerializer
from contacts.serializers import CustomerSerializer
from acknowledgements.serializers import AcknowledgementSerializer


logger = logging.getLogger(__name__)


class DealSerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, allow_null=True)
    customer = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Customer.objects.all())
    contact = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Contact.objects.all())
    acknowledgement = AcknowledgementSerializer(required=False, allow_null=True)
    quotation = EstimateSerializer(required=False, allow_null=True)
    #employee = serializers.PrimaryKeyRelatedField(read_only=True, queryset=User.objects.all())
    status = serializers.CharField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_null=True)
    last_contacted = serializers.DateField(required=False, allow_null=True)
    total = serializers.DecimalField(decimal_places=2, max_digits=12, required=False, allow_null=True)
    
    class Meta:
        model = Deal
        read_only_fields = ('last_modified', 'employee')
        exclude = ()
        
    def create(self, validated_data):
        
        description = validated_data.pop('description', 'New Deal')
        employee = self.context['request'].user
        
        instance = self.Meta.model.objects.create(description=description, employee=employee, **validated_data)
        
        return instance
        
    def to_representation(self, instance):
        
        ret = super(DealSerializer, self).to_representation(instance)
        
        try:
            serializer = CustomerSerializer(instance.customer)
            ret['customer'] = serializer.data
        except AttributeError as e:
            logger.debug(e)
        
        try:
            ret['contact'] = {'id': instance.contact.id,
                              'name': instance.contact.name,
                              'email': instance.contact.email,
                              'telephone': instance.contact.telephone}
        except AttributeError as e:
            pass
                          
        return ret