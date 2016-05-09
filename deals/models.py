#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from datetime import datetime, date
from django.db import models

from contacts.models import Contact, Customer
from acknowledgements.models import Acknowledgement
from estimates.models import Estimate


logger = logging.getLogger(__name__)


class Deal(models.Model):
    description = models.TextField(null=False)
    customer = models.ForeignKey(Customer, null=True)
    contact = models.ForeignKey(Contact, related_name="deals", null=True)
    acknowledgement = models.ForeignKey(Acknowledgement, null=True)
    quotation = models.ForeignKey(Estimate, null=True)
    status = models.TextField(null=True)
    notes = models.TextField(null=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_modified = models.DateTimeField(auto_now=True)
    last_contacted = models.DateField(default=date.today())