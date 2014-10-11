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


logger = logging.getLogger(__name__)


class EquipmentResource(ModelResource):
    
    class Meta:
        queryset = Equipment.objects.all()
        resource_name = 'equipment'
        always_return_data = True
        authorization = DjangoAuthorization()
        ordering = ['description', 'brand']
    
    def hydrate(self, bundle):
        logger.debug(bundle.obj.__dict__)
        if "equipment_id" in bundle.data:
            e_id = bundle.data['equipment_id'].split('-')
            try:
                e_id = e_id[1]
            except IndexError:
                e_id = e_id[0]
                
            bundle.obj.id = e_id
            
        return bundle
        
    def obj_create(self, bundle, **kwargs):
        """
        Creates the equipmemt
        """
        #Initial supply creation
        bundle = super(EquipmentResource, self).obj_create(bundle, **kwargs)        
            
        return bundle