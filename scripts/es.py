#!/usr/local/bin/python
# -*- coding: utf-8 -*-
"""
PDF pages for stickers
"""
import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
from django.conf import settings
import logging
from decimal import Decimal
from pytz import timezone
import math

from django.db import models
from django.contrib.auth.models import User
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from reportlab.lib import colors, utils
from reportlab.lib.units import mm
from reportlab.platypus import *
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.graphics.barcode import code128

from hr.models import Employee
from media.stickers import StickerPage

logger = logging.getLogger(__name__)

pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))


django.setup()
        
if __name__ == "__main__":
    
        e1 = Employee.objects.get(pk=11000055)
        e2 = Employee.objects.get(pk=11000133)
        codes = [('DREM-{0}'.format(e1.id), u'{0}'.format(e1.name)), ('DREM-{0}'.format(e2.id), u'{0}'.format(e2.name))]
        sp = StickerPage(codes=codes)
        sp.create("EmployeeStickers.pdf")
            
            
    
    
    
    
    
    
    
    
    