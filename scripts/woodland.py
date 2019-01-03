#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import csv
import os
import requests
import json
import hashlib
import time
import math
import subprocess
import pprint
import logging
import copy
from time import sleep
from decimal import Decimal
from datetime import datetime, timedelta, date
from dateutil import parser
from threading import Thread, active_count

sys.path.append('/Users/Charlie/Sites/employee/backend')
sys.path.append('/home/django_worker/backend')

from django.core.wsgi import get_wsgi_application

os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
application = get_wsgi_application()
pp = pprint.PrettyPrinter(width=1, indent=1)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

import boto
import textract
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LTPage, LTChar, LTAnno, LAParams, LTTextBox, LTTextLine, LTTextBoxHorizontal
from django.db.models import Count
from django.contrib.auth.models import Group

from contacts.models import Customer
from acknowledgements.models import Acknowledgement as A
from trcloud.models import TRSalesOrder as SO
from estimates.models import Estimate as E
from po.models import PurchaseOrder as PO
from hr.models import Attendance, Employee
from hr.PDF import AttendancePDF
from supplies.models import Log, Supply, Product
from administrator.models import User 
from media.models import DriveObject
from media.models import S3Object
from utilities.queue import Queue



if __name__ == '__main__':

    g = Group.objects.get(name='God')

    logger.debug(g.__dict__)
    

    # def populate(queue, s_objs):
    #     for s in s_objs[0:50]:
    #         queue.enqueue(Thread(target=s._update_from_key_obj))
        
    #     logger.debug(queue.queue)

    # queue = Queue()

    # s_objs = S3Object.objects.filter(_size=None).order_by('-id')

    # init_t = Thread(target=populate, args=(queue, s_objs))
    # init_t.start()

    # sleep(2)

    # while queue.size > 0:
    #     sleep(2)
    #     ac = active_count()

    #     if ac < 50:
    #         for x in xrange(50 - ac):
    #             if queue.size > 0:
    #                 t = queue.dequeue(750)
    #                 t.start()
        

    """
    s_re = r'(acknowledgement|acknowledgment|estimate|purchase_order)\/(Acknowledgement|Estimate|PO|Quality_Control|Label|Production|Quotation)\-(\d+)((?:\-\S+)*.pdf)'
    
    s_objs = S3Object.objects.filter(bucket='document.dellarobbiathailand.com', key__regex=s_re, key__icontains='estimate').order_by('-id')

    logger.debug(len(s_objs))
    for s in s_objs[0:50]:
        try:
            s.migrate()
        except AttributeError as e:
            logger.debug(s.__dict__)
    """

    """

    conn = boto.s3.connect_to_region('ap-southeast-1')
    bucket = conn.get_bucket('document.dellarobbiathailand.com', True)
    bucket.configure_versioning(True)

    key_list = bucket.list()

    dupes_list = S3Object.objects.filter(bucket='document.dellarobbiathailand.com') \
                                 .order_by('-id') \
                                 .values('key', 'version_id') \
                                 .annotate(Count('key'), Count('version_id')) \
                                 .order_by('key') \
                                 .filter(key__count__gt=1, version_id__count__gt=1)
    
    dupes_list = [i for i in sorted(dupes_list, key=lambda x: x['key'])]

    logger.debug(pp.pformat(dupes_list))
    

    #dupes_list = []

    
    for key in dupes_list:

        key_name = key['key']
        print('\n\n\n')
        print(''.join(['-' for i in xrange(80)]))
        #msg = u'{0} : {1} : {2} : {3}'.format(s.id, s.last_modified, s.key, s.version_id)
        logger.debug(key_name)
        print('\n\n')


        s_objs = S3Object.objects.filter(key=key_name, version_id=key['version_id']).order_by('-last_modified', '-id')

        assert len(s_objs) == key['version_id__count'], "Number of objects should be equal"

        keys = sorted(bucket.list_versions(prefix=key_name), key=lambda x: x.last_modified, reverse=True)
        for index, k in enumerate(keys):
            try:
                s = s_objs[index]
                msg = u' {0} : {1} | {2} | {3} : {4}'.format(s.last_modified,
                                                             k.last_modified,
                                                             k.key, 
                                                             s.version_id,
                                                             k.version_id)
                logger.debug(msg)

                #s.last_modified = parser.parse(k.last_modified)
                #s.version_id = k.version_id
                #s._size = k.size
                #s.save()
            except AttributeError as e:
                logger.error(e)
            except IndexError as e:
                logger.error(e)
                
                #S3Object.objects.create(key=key_name, 
                #                        bucket=bucket.name,
                #                        _size=k.size,
                #                        version_id=k.version_id,
                #                        last_modified=parser.parse(k.last_modified))
                

        print(''.join(['-' for i in xrange(80)]))
    """
