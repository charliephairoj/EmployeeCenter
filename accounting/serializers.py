#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from datetime import date
from decimal import Decimal

from rest_framework import serializers

from accounting.models import Account, Transaction, Journal, JournalEntry
from accounting.journal_entry import service as je_service
from accounting.transaction import service as tr_service
from hr.models import Employee
from media.models import S3Object
from media.serializers import S3ObjectSerializer
from pytz import timezone


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class TransactionFieldSerializer(serializers.ModelSerializer):
    debit = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    credit = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    date = serializers.DateTimeField(source="transaction_date", read_only=True)

    class Meta:
        fields = ['id', 'debit', 'date', 'credit', 'description']
        model = Transaction


class AccountFieldSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)

    class Meta:
        fields = ['id', 'name']
        model = Account


class JournalEntryFieldSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['id', 'description']
        model = JournalEntry


class TransactionListSerializer(serializers.ListSerializer):
    def validate(self, data):

        if sum([tr['credit'] or Decimal('0') for tr in data]) != sum(tr['debit'] or Decimal('0') for tr in data):
            raise serializers.ValidationError("The credits and debits should balance out")
        
        return data


class TransactionSerializer(serializers.ModelSerializer):
    account = AccountFieldSerializer(required=True)
    journal_entry = JournalEntryFieldSerializer(required=False)
    debit = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    credit = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    date = serializers.DateTimeField(source="transaction_date", read_only=True)

    class Meta:
        fields = ['id', 'debit', 'date', 'credit', 'description', 'journal_entry', 'account']
        model = Transaction
        list_serializer_class = TransactionListSerializer

    def to_internal_value(self, data):

        ret = super(TransactionSerializer, self).to_internal_value(data)

        if 'journal_entry' in ret:
            if not isinstance(ret['journal_entry'], JournalEntry):
                ret['journal_entry'] = JournalEntry.objects.get(pk=data['journal_entry']['id'])

        if not isinstance(ret['account'], Account):
            ret['account'] = Account.objects.get(pk=data['account']['id'])

        return ret
    
    def create(self, validated_data):

        description = validated_data.get('description')
        credit = validated_data.get('credit', Decimal('0'))
        debit = validated_data.get('debit', Decimal('0'))
        date = validated_data.get('date', None)
        je = validated_data.get('journal_entry', self.context['journal_entry'])
        acc = validated_data.get('account')
        
        instance = tr_service.create(journal_entry=je,
                                     account=acc,
                                     description=description,
                                     credit=credit,
                                     debit=debit,
                                     transaction_date=date)
                                            
        return instance


class JournalFieldSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="name_en", required=False)

    class Meta:  
        fields = ['id', 'name']
        model = Journal
    

class AccountSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    account_code = serializers.CharField(required=False, allow_null=True)
    name_en = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    name_th = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    type = serializers.CharField(required=False, allow_null=True)
    type_detail = serializers.CharField(required=False, allow_null=True)
    transactions = TransactionFieldSerializer(many=True, read_only=True)
 
    
    class Meta:
        fields = '__all__'
        model = Account
    
    def __init__(self, *args, **kwargs):

        super(AccountSerializer, self).__init__(*args, **kwargs)

        if "pk" not in self.context['view'].kwargs:
            self.fields.pop('transactions')


class JournalEntrySerializer(serializers.ModelSerializer):
    journal = JournalFieldSerializer(required=True)
    date = serializers.DateField(required=False, default=serializers.CreateOnlyDefault(date.today()))
    description = serializers.CharField(required=True, allow_blank=False)
    transactions = TransactionSerializer(many=True, allow_empty=False)

    class Meta:
        fields = '__all__'
        model = JournalEntry

    def to_internal_value(self, data):

        ret = super(JournalEntrySerializer, self).to_internal_value(data)

        if not isinstance(ret['journal'], Journal):
            ret['journal'] = Journal.objects.get(pk=data['journal']['id'])

        return ret
    
    def create(self, validated_data):
        transactions_data = self.initial_data.pop('transactions')
        
        date = validated_data.get('date', None)

        instance = je_service.create(journal=validated_data['journal'],
                                     description=validated_data['description'],
                                     date=date)

        tr_serializer = TransactionSerializer(data=transactions_data, many=True, context={'journal_entry': instance})
        if tr_serializer.is_valid(raise_exception=True):
            tr_serializer.save()
                                            
        return instance


    def validate_transactions(self, transactions):

        if sum([tr['credit'] or Decimal('0') for tr in transactions]) != sum(tr['debit'] or Decimal('0') for tr in transactions):
            raise serializers.ValidationError("The credits and debits should balance out")
        
        return transactions
    