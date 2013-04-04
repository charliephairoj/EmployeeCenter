import os
import json
import logging
import time

from django.contrib.auth.decorators import login_required

from accounting.models import Transaction
from utilities.http import processRequest


logger = logging.getLogger('EmployeeCenter')


# Create your views here.
@login_required
def transaction(request, transaction_id=0):
    return processRequest(request, Transaction, transaction_id)
