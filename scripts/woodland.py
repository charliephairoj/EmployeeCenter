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
from decimal import Decimal
from datetime import datetime, timedelta, date

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


def get_url_getter(conn, bucket):

    def get_url(key, time=86400, force_http=False):
        return conn.generate_url(time,
                                'GET',
                                bucket=bucket,
                                key=key,
                                force_http=force_http)

    return get_url


def get_customer_name(layout_element):
    return layout_element.get_text().split('\n', 1)[0]


def get_order_data(k):
    order = {'id': k['id'], 'items': []}
    filename = "Quotation-{0}.pdf".format(k['id'])
    k['key'].get_contents_to_filename(filename)
    fp = open(filename, 'rb')
    parser = PDFParser(fp)

    document = PDFDocument(parser)
    if not document.is_extractable:
        raise PDFTextExtractionNotAllowed
    # Create a PDF resource manager object that stores shared resources.
    rsrcmgr = PDFResourceManager()
    # Set parameters for analysis.
    laparams = LAParams()
    # Create a PDF page aggregator object.
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    qp = {'quantities': [], 'prices': [], 'price_y': []}

    for page in PDFPage.create_pages(document):
        interpreter.process_page(page)
        # receive the LTPage object for the page.
        layout = device.get_result()
        for a in layout:

            if isinstance(a, LTTextBoxHorizontal):
                if math.floor(a.x0) == 122 and math.floor(a.y1) == 695:
                    order['customer'] = get_customer_name(a)
        

                elif math.floor(a.x0) in [111, 98]:

                    products_str = a.get_text().replace('Description\n', '')
                    item = {}

                    if 'comments' in products_str.lower():
                        products_str, item['comments'] = products_str.split('Comments:')

                    for index, b in enumerate([s for s in products_str.split('\n') if s != '']):
                        if index == 0:
                            item['description'] = b
                        if index > 0 and b[0] != ' ' and item.has_key('width'):
                            order['items'].append(copy.deepcopy(item))
                            item = {'description': b, 'comments': ''}

                        if "width" in b.lower():
                            d = b.replace('\n', '').replace('mm', '').strip()
                            for dimension in [
                                ('height', 'Height: '), 
                                ('depth', 'Depth: '), 
                                ('width', 'Width: ')]:
                                d, item[dimension[0]] = d.split(dimension[1]) if len(d.split(dimension[1])) == 2 else (d, 0)
                        elif b[0] == ' ':
                            logger.debug(b)
                            #item['comments'] += b
                    if item.has_key('description'):
                        order['items'].append(copy.deepcopy(item))

                # Process prices
                elif math.floor(a.x0) in [383, 390, 397, 408, 411, 402, 391]:
                    try:
                        qp['prices'].append(Decimal(a.get_text().replace('\n', '').replace('Unit Price', '').replace(',', '')))
                        qp['price_y'].append(a.y0)
                    except Exception as e:
                        logger.warn(e)
                elif math.floor(a.x0) in [459, 464, 457, 477, 455, 422]:
                    if a.y0 in qp['price_y']:
                        qp['quantities'].append(Decimal(a.get_text().replace('\n', '').replace('Qty', '')))

                elif "vat" in a.get_text().lower():
                    order['vat'] = Decimal(a.get_text().split('Vat ')[-1][0])

                else:
                    logger.debug("{0} : {1} | {2}".format(a.x0, a.y0, a))
                

    # Apply prices and quantites
    err_msg = "{0} : {1} | {2} ... {3}".format(len(qp['quantities']), len(qp['prices']), len(order['items']), order['items'])
    assert len(qp['quantities']) == len(qp['prices']) and len(qp['quantities']) == len(order['items']), err_msg

    for index in  xrange(len(qp['prices'])):
        order['items'][index]['price'] = qp['prices'][index]
        order['items'][index]['quantity'] = qp['quantities'][index]

    os.remove(filename)

    return order        



if __name__ == '__main__':
    # Remove duplicate products

    last_quotation = E.objects.exclude(id__gt=16000).order_by('-id')[0]

    conn = boto.s3.connect_to_region('ap-southeast-1')

    bucket = conn.get_bucket('document.dellarobbiathailand.com')

    keys = bucket.get_all_keys(prefix='estimate')

    get_url = get_url_getter(conn, bucket)

    new_keys = []
    orders = []
    error_orders = []


    for k in keys:
        q_id = int(k.key.split('-')[1].split('.')[0])
        if q_id > last_quotation.id:
            new_keys.append({'id': q_id, 'key': k})


    for k in new_keys:
        try:
            orders.append(get_order_data(k))
        except AssertionError as e:
            error_orders.append(k)

    with open('error_quotations.csv', mode='w') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(['ID', 'key', 'url'])
        for k in error_orders:
            writer.writerow([k['id'], k['key'].key, get_url(k['key'])])
            logger.debug("Quotation-{0}.pdf".format(k['id']))

    



