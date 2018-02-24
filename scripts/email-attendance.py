#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import logging
import pprint
from datetime import datetime, timedelta, date

sys.path.append('/Users/Charlie/Sites/employee/backend')
sys.path.append('/home/django_worker/backend')

from django.core.wsgi import get_wsgi_application

os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
application = get_wsgi_application()
pp = pprint.PrettyPrinter(width=1, indent=1)
logger = logging.getLogger(__name__)

from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

import boto

from hr.models import Attendance, Employee
from hr.PDF import AttendancePDF


if __name__ == '__main__':
    ed = date.today()

    m = abs(ed.month - 1) or 12 if ed.day <= 25 else ed.month
    y = ed.year if ed > date(ed.year, 1, 25) else ed.year - 1
    sd = date(y, m, 26)

    employees = Employee.objects.filter(status='active').order_by('-nationality')

    pdf = AttendancePDF(start_date=sd, end_date=ed, employees=employees)
    filename = pdf.create()


    # via http://codeadict.wordpress.com/2010/02/11/send-e-mails-with-attachment-in-python/
    subject = "Attendance from {0} to {1}".format(sd.strftime('%B %d, %Y'), ed.strftime('%B %d, %Y'))
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = 'noreply@alineagroup.co'
    msg['To'] = 'hr@alineagroup.co'

    # what a recipient sees if they don't use an email reader
    msg.preamble = 'Multipart message.\n'

    # the message body
    part = MIMEText(subject)
    msg.attach(part)

    # the attachment
    part = MIMEApplication(open(filename, 'rb').read())
    part.add_header('Content-Disposition', 'attachment', filename='Attendance.pdf')
    msg.attach(part)

    # connect to SES
    connection = boto.connect_ses()

    # and send the message
    result = connection.send_raw_email(msg.as_string()
        , source=msg['From']
        , destinations=[msg['To']])
    logger.debug(result)

    os.remove(filename)