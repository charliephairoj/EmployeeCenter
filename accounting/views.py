import os
import json
import logging
import time

from django.contrib.auth.decorators import login_required
from django.conf import settings
from rest_framework import viewsets
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import authentication, permissions

from accounting.models import Account, Transaction
from accounting.serializers import AccountSerializer


logger = logging.getLogger(__name__)


class AccountMixin(object):
    queryset = Account.objects.all().order_by('code')
    serializer_class = AccountSerializer
    
    def handle_exception(self, exc):
        """
        Custom Exception Handler
        
        Exceptions are logged as error via logging, 
        which will send an email to the system administrator
        """
        logger.error(exc)        
        
        return super(AccountMixin, self).handle_exception(exc)
    
    
class AccountList(AccountMixin, generics.ListCreateAPIView):
        
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset.all()
        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(name_en__icontains=query) |
                                       Q(name_th__icontains=query) |
                                       Q(id__icontains=query))

        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
        elif not offset and limit:
            queryset = queryset[:limit]
        else:
            queryset = queryset[0:50]
            
        return queryset
        
    def get_paginate_by(self):
        """
        
        """
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if limit == 0:
            return self.queryset.count()
        else:
            return limit
            

class AccountDetail(AccountMixin, generics.RetrieveUpdateDestroyAPIView):
    pass