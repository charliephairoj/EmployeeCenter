from __future__ import unicode_literals
import logging

from django.db import models


logger = logging.getLogger(__name__)


class Quotation(models.Model):
    trcloud_id = models.IntegerField()
    
    def _create_in_trcloud(self):

        # Reconcile customer with TRCloud

        # Prepare the data package

        # Convert to JSON

        # Send the data to TRCloud endpoint for Alinea

    def _update_in_trcloud(self):

        # Reconcile customer with TRCloud

        # Prepare the data package

        # Convert to JSON

        # Send the data to TRCloud endpoint for Alinea
    
