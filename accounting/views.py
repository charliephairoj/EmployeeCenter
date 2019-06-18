import os
import json
import logging
import time

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.conf import settings
from rest_framework import viewsets
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import authentication, permissions

from accounting.models import Account, Transaction
from accounting.serializers import AccountSerializer


logger = logging.getLogger(__name__)


class AccountMixin(object):
    serializer_class = AccountSerializer
    
    def get_queryset(self):

        user = self.request.user
        company = user.company
        logger.info(company)
        qs = Account.objects.filter(company=company).order_by('type', 'type_detail')
        qs = qs.annotate(debit_sum=Sum('transactions__debit'), credit_sum=Sum('transactions__credit'))

        return qs 
        
    def handle_exception(self, exc):
        """
        Custom Exception Handler
        
        Exceptions are logged as error via logging, 
        which will send an email to the system administrator
        """
        logger.error(exc)        
        
        return super(AccountMixin, self).handle_exception(exc)
    
    
class AccountList(AccountMixin, generics.ListCreateAPIView):
        
    def filter_queryset(self, queryset):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = queryset.filter(parent__isnull=True)

        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(name__icontains=query) |
                                       Q(name_th__icontains=query) |
                                       Q(type__icontains=query) |
                                       Q(id__icontains=query))

        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
        elif not offset and limit:
            queryset = queryset[:limit]
        else:
            queryset = queryset[0:50]

        queryset = queryset.select_related('parent',
                                           'company')

        queryset = queryset.prefetch_related('sub_accounts', 
                                             'sub_accounts__parent',
                                             'sub_accounts__company',
                                             'transactions',
                                             'sub_accounts__transactions',
                                             'sub_accounts__sub_accounts')
            
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
    def filter_queryset(self, queryset):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = queryset.select_related('parent',
                                           'company')

        queryset = queryset.prefetch_related('sub_accounts', 
                                             'sub_accounts__parent',
                                             'sub_accounts__company',
                                             'sub_accounts__transactions',
                                             'transactions')

            
        return queryset