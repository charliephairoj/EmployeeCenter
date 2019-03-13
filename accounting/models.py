from decimal import Decimal
import dateutil.parser
import logging

from django.db import models
from administrator.models import User, Company
from contacts.models import Contact


logger = logging.getLogger(__name__)


class Journal(models.Model):
    name_en = models.TextField()
    name_th = models.TextField()


class JournalEntry(models.Model):
    description = models.TextField()
    date = models.DateField(auto_now=True)
    journal = models.ForeignKey(Journal)
    

class Account(models.Model):
<<<<<<< HEAD
    id = models.TextField(primary_key=True, unique=True)
    account_code = models.TextField(db_column='code')
    name = models.TextField(db_column='name_en')
=======
    code = models.TextField(null=True)
    name_en = models.TextField(null=True)
>>>>>>> accounting
    name_th = models.TextField(null=True)
    type = models.TextField(db_column="account_type", null=True)
    company = models.ForeignKey(Company, related_name="chart_of_accounts")
    

class Transaction(models.Model):
    account = models.ForeignKey(Account)
    journal_entry = models.ForeignKey(JournalEntry)
    debit = models.DecimalField(decimal_places=2, max_digits=12)
    credit = models.DecimalField(decimal_places=2, max_digits=12)
    balance = models.DecimalField(decimal_places=2, max_digits=12)
    transaction_id = models.TextField()
    description = models.TextField()
    transaction_date = models.DateTimeField()

    class Meta:
        permissions = (('can_view_transactions', 'Can View Transactions'),)

<<<<<<< HEAD
=======

# Not yet created in database 
class Invoice(models.Model):
    tax_id = models.TextField(null=True)
    issue_date = models.DateTimeField(null=True)
    due_date = models.DateTimeField(null=True)
    tax_date = models.DateTimeField(null=True)
    discount = models.TextField(default=0)
    vat = models.TextField(default=7)
    total = models.DecimalField()
    grand_total = models.DecimalField()
    fiscal_year = models.TextField(null=True)
    invoice_number = models.TextField(null=True)

>>>>>>> accounting

    # TRCloud Attributes
    trcloud_invoice_id = models.IntegerField(null=True)
    trcloud_company_id = models.IntegerField(null=True)
    trcloud_user_id = models.IntegerField(null=True)
    trcloud_company_format = models.TextField(null=True)
    trcloud_contact_id = models.TextField(null=True)

    """
    
  `contact_id` int(11) unsigned DEFAULT NULL COMMENT 'contact_id จาก contact-table',
  `title` varchar(30) NOT NULL,
  `name` varchar(75) DEFAULT NULL,
  `organization` varchar(100) DEFAULT NULL,
  `branch` varchar(40) DEFAULT NULL,
  `address` mediumtext,
  `telephone` varchar(100) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `tax_id` varchar(75) DEFAULT NULL,
  `issue_date` date DEFAULT NULL,
  `due_date` date DEFAULT NULL,
  `tax_date` date DEFAULT NULL,
  `billing_note_date` date DEFAULT NULL,
  `billing_note_due` date DEFAULT NULL,
  `billing_note_note` text NOT NULL,
  `discount` varchar(12) DEFAULT NULL,
  `ref_total` decimal(20,3) DEFAULT NULL,
  `invoice_note` text,
  `status` varchar(12) NOT NULL DEFAULT 'New',
  `payment` double NOT NULL DEFAULT '0',
  `reference` varchar(50) NOT NULL DEFAULT '' COMMENT 'เลขที่เอกสารอ้างอิง',
  `reference_id` int(11) NOT NULL,
  `tax_option` varchar(2) NOT NULL DEFAULT 'ex' COMMENT 'ราคา in = include หรือ ex = exclude',
  `type` varchar(50) NOT NULL DEFAULT 'ar' COMMENT 'cash/ar/Credit Card',
  `salesman` varchar(50) NOT NULL,
  `department` varchar(50) NOT NULL,
  `project` varchar(50) NOT NULL,
  `url` tinytext NOT NULL,
  `quotation` varchar(40) NOT NULL,
  `bill` varchar(40) NOT NULL,
  `billing_note` varchar(40) NOT NULL,
  `receipt` varchar(40) NOT NULL,
  `pos` varchar(12) NOT NULL COMMENT 'pos = pos/ empty = normal / deposit = มัดจำ / last_deposit = มัดจำงวดสุดท้าย',
  `credit_note` varchar(20) NOT NULL DEFAULT '0',
  `wht` varchar(20) NOT NULL,
  `update_dt` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00' ON UPDATE CURRENT_TIMESTAMP,
  `gl_entry` tinytext NOT NULL,
  `deposit_amount` varchar(24) NOT NULL,
  `legacy` varchar(3) NOT NULL,
  `create_by` varchar(20) NOT NULL,
  `engine_reference` int(11) NOT NULL,
  `approve_status` varchar(4) NOT NULL COMMENT '_ = nothing, yes = pass, no = fail, wait = wait',
  `approve_id` int(10) unsigned NOT NULL,
  `approve_date` date NOT NULL,
  `sum_quantity` int(11) NOT NULL,
  `create_dt` datetime NOT NULL,
  `tax_report` varchar(4) NOT NULL DEFAULT 'yes' COMMENT 'yes | no',
  `doc_type` varchar(10) NOT NULL DEFAULT 'iv' COMMENT 'iv = invoice | cn = credit_note | cd = cash discount',
  `warehouse` varchar(50) NOT NULL,
  `fx` varchar(3) NOT NULL COMMENT 'สกุลเงิน เช่น THB USD ถ้าว่างคือ สกุลหลัก',
  `rate` double unsigned NOT NULL DEFAULT '1' COMMENT 'อัตราแลกเปลี่ยน',
  `other` text NOT NULL,
  `cn2_original` double unsigned NOT NULL COMMENT 'มูลค่าก่อนลดหนี้ cn2',
  PRIMARY KEY (`invoice_id`),
  KEY `company_id` (`company_id`)
"""
