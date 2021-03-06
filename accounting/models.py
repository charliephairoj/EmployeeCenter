#!/usr/bin/env python
# -*- coding: utf-8 -*-
from decimal import Decimal
import dateutil.parser
import logging
from datetime import datetime, date

from django.db import models
from django.db.models import Sum
from administrator.models import User, Company


logger = logging.getLogger(__name__)


class Journal(models.Model):
    name_en = models.TextField()
    name_th = models.TextField()
    company = models.ForeignKey(Company)

    @property
    def name(self):
        return self.name_en

    @name.setter
    def name(self, value):
        self.name_en = value


class JournalEntry(models.Model):
    description = models.TextField()
    date = models.DateField(default=date.today)
    journal = models.ForeignKey(Journal)
    

class Account(models.Model):
    id = models.AutoField(primary_key=True)
    account_code = models.TextField(db_column='code', null=True)
    name = models.TextField(db_column='name_en')
    name_th = models.TextField(null=True)
    type = models.TextField(db_column="account_type", null=True)
    type_detail = models.TextField(null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="chart_of_accounts")
    parent = models.ForeignKey('self', related_name='sub_accounts', null=True)

    @property
    def balance(self):
        #qs = self.transactions.all()
        #totals = qs.aggregate(Sum('debit'), Sum('credit'))
        #return abs((totals['debit__sum'] or 0) - (totals['credit__sum'] or 0)) 
        try:
            return abs((self.debit_sum or 0) - (self.credit_sum or 0))
        except Exception as e:
            return 0

class Transaction(models.Model):
    account = models.ForeignKey(Account, related_name='transactions')
    journal_entry = models.ForeignKey(JournalEntry, related_name='transactions')
    debit = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True)
    credit = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True)
    #balance = models.DecimalField(decimal_places=2, max_digits=12)
    #transaction_id = models.TextField()
    description = models.TextField()
    transaction_date = models.DateTimeField(default=datetime.now)

    class Meta:
        permissions = (('can_view_transactions', 'Can View Transactions'),)

    @property
    def date(self):
        return self.transaction_date

    @date.setter
    def date(self, value):
        self.transaction_date = value


# Not yet created in database 
# class Invoice(models.Model):
#     tax_id = models.TextField(null=True)
#     issue_date = models.DateTimeField(null=True)
#     due_date = models.DateTimeField(null=True)
#     tax_date = models.DateTimeField(null=True)
#     discount = models.TextField(default=0)
#     vat = models.TextField(default=7)
#     total = models.DecimalField()
#     grand_total = models.DecimalField()
#     fiscal_year = models.TextField(null=True)
#     invoice_number = models.TextField(null=True)


#     # TRCloud Attributes
#     trcloud_invoice_id = models.IntegerField(null=True)
#     trcloud_company_id = models.IntegerField(null=True)
#     trcloud_user_id = models.IntegerField(null=True)
#     trcloud_company_format = models.TextField(null=True)
#     trcloud_contact_id = models.TextField(null=True)

# u"""
    
#   `contact_id` int(11) unsigned DEFAULT NULL COMMENT 'contact_id จาก contact-table',
#   `title` varchar(30) NOT NULL,
#   `name` varchar(75) DEFAULT NULL,
#   `organization` varchar(100) DEFAULT NULL,
#   `branch` varchar(40) DEFAULT NULL,
#   `address` mediumtext,
#   `telephone` varchar(100) DEFAULT NULL,
#   `email` varchar(100) DEFAULT NULL,
#   `tax_id` varchar(75) DEFAULT NULL,
#   `issue_date` date DEFAULT NULL,
#   `due_date` date DEFAULT NULL,
#   `tax_date` date DEFAULT NULL,
#   `billing_note_date` date DEFAULT NULL,
#   `billing_note_due` date DEFAULT NULL,
#   `billing_note_note` text NOT NULL,
#   `discount` varchar(12) DEFAULT NULL,
#   `ref_total` decimal(20,3) DEFAULT NULL,
#   `invoice_note` text,
#   `status` varchar(12) NOT NULL DEFAULT 'New',
#   `payment` double NOT NULL DEFAULT '0',
#   `reference` varchar(50) NOT NULL DEFAULT '' COMMENT 'เลขที่เอกสารอ้างอิง',
#   `reference_id` int(11) NOT NULL,
#   `tax_option` varchar(2) NOT NULL DEFAULT 'ex' COMMENT 'ราคา in = include หรือ ex = exclude',
#   `type` varchar(50) NOT NULL DEFAULT 'ar' COMMENT 'cash/ar/Credit Card',
#   `salesman` varchar(50) NOT NULL,
#   `department` varchar(50) NOT NULL,
#   `project` varchar(50) NOT NULL,
#   `url` tinytext NOT NULL,
#   `quotation` varchar(40) NOT NULL,
#   `bill` varchar(40) NOT NULL,
#   `billing_note` varchar(40) NOT NULL,
#   `receipt` varchar(40) NOT NULL,
#   `pos` varchar(12) NOT NULL COMMENT 'pos = pos/ empty = normal / deposit = มัดจำ / last_deposit = มัดจำงวดสุดท้าย',
#   `credit_note` varchar(20) NOT NULL DEFAULT '0',
#   `wht` varchar(20) NOT NULL,
#   `update_dt` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00' ON UPDATE CURRENT_TIMESTAMP,
#   `gl_entry` tinytext NOT NULL,
#   `deposit_amount` varchar(24) NOT NULL,
#   `legacy` varchar(3) NOT NULL,
#   `create_by` varchar(20) NOT NULL,
#   `engine_reference` int(11) NOT NULL,
#   `approve_status` varchar(4) NOT NULL COMMENT '_ = nothing, yes = pass, no = fail, wait = wait',
#   `approve_id` int(10) unsigned NOT NULL,
#   `approve_date` date NOT NULL,
#   `sum_quantity` int(11) NOT NULL,
#   `create_dt` datetime NOT NULL,
#   `tax_report` varchar(4) NOT NULL DEFAULT 'yes' COMMENT 'yes | no',
#   `doc_type` varchar(10) NOT NULL DEFAULT 'iv' COMMENT 'iv = invoice | cn = credit_note | cd = cash discount',
#   `warehouse` varchar(50) NOT NULL,
#   `fx` varchar(3) NOT NULL COMMENT 'สกุลเงิน เช่น THB USD ถ้าว่างคือ สกุลหลัก',
#   `rate` double unsigned NOT NULL DEFAULT '1' COMMENT 'อัตราแลกเปลี่ยน',
#   `other` text NOT NULL,
#   `cn2_original` double unsigned NOT NULL COMMENT 'มูลค่าก่อนลดหนี้ cn2',
#   PRIMARY KEY (`invoice_id`),
#   KEY `company_id` (`company_id`)
# """
