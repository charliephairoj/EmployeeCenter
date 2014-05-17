"""
API file for equipment
"""
from decimal import Decimal
from datetime import datetime, timedelta
import time
import logging
import json
import re

from django.db.models import Q
from django.conf.urls import url
from tastypie import fields
from tastypie.resources import ModelResource
from tastypie.authorization import DjangoAuthorization
from tastypie.exceptions import Unauthorized

from equipment.models import Equipment


class EquipmentResource(ModelResource):
    
    class Meta:
        queryset = Equipment.objects.all()
        resource_name = 'equipment'
        always_return_data = True
        authorization = DjangoAuthorization()
        ordering = ['description', 'brand']
        