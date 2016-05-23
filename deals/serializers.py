#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from decimal import Decimal
from pytz import timezone
from datetime import datetime, date
from dateutil import parser

import boto
from rest_framework import serializers
from rest_framework.fields import DictField
from django.contrib.auth.models import User

from deals.models import Deal, Event as DealEvent
from contacts.models import Contact, Customer
from acknowledgements.models import Acknowledgement
from estimates.models import Estimate
from estimates.serializers import EstimateSerializer
from contacts.serializers import CustomerSerializer
from acknowledgements.serializers import AcknowledgementSerializer


logger = logging.getLogger(__name__)


class DealSerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, allow_null=True)
    customer = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Customer.objects.all(), write_only=True)
    contact = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Contact.objects.all())
    acknowledgement = AcknowledgementSerializer(required=False, allow_null=True)
    quotation = EstimateSerializer(required=False, allow_null=True)
    #employee = serializers.PrimaryKeyRelatedField(read_only=True, queryset=User.objects.all())
    status = serializers.CharField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_null=True)
    last_contacted = serializers.DateTimeField(required=False, allow_null=True)
    total = serializers.DecimalField(decimal_places=2, max_digits=12, required=False, allow_null=True)
    events = serializers.ListField(child=serializers.DictField(), required=False, allow_null=True, write_only=True)

    class Meta:
        model = Deal
        read_only_fields = ('last_modified', 'employee')
        exclude = ()

    def create(self, validated_data):

        description = validated_data.pop('description', 'New Deal')
        employee = self.context['request'].user

        instance = self.Meta.model.objects.create(description=description, employee=employee, **validated_data)

        return instance

    def update(self, instance, validated_data):
        # Extract deal stage for later comparison
        new_status = validated_data.get('status', instance.status)
        old_status = instance.status
        events_data = validated_data.pop('events', [])

        instance = super(DealSerializer, self).update(instance, validated_data)

        # Create any new events
        for event_data in events_data:
            if 'id' not in event_data:
                oa = parser.parse(event_data['occurred_at'])
                e = DealEvent.objects.create(description=event_data['description'],
                                             notes=event_data.get('notes', None),
                                             occurred_at=oa,
                                             deal=instance)

                # Set the new 'last contacted' date if applicable
                eoa = e.occurred_at
                ilc = instance.last_contacted
                last_contacted =  eoa if eoa > ilc else ilc
                instance.last_contacted = last_contacted
        # Log change in deal stage
        if new_status != old_status:
            description = "Moved deal from {0} to {1}".format(old_status.title(),
                                                              instance.status.title())
            DealEvent.objects.create(deal=instance,
                                     description=description)

        # Final save
        instance.save()

        return instance

    def to_representation(self, instance):

        ret = super(DealSerializer, self).to_representation(instance)

        ret['customer'] = {'id': instance.customer.id,
                           'name': instance.customer.name}

        # Actions to take if the a single resource is requested
        pk = self.context['view'].kwargs.get('pk', None)
        if pk or self.context['request'].method.lower() in ['put', 'post']:
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

            try:
                ret['events'] = [{'id': e.id,
                                  'description': e.description,
                                  'notes': e.notes,
                                  'occurred_at': e.occurred_at} for e in instance.events.all()]
            except Exception as e:
                logger.warn(e)

        return ret
         
