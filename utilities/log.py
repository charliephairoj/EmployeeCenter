import logging
import sys
import warnings

import boto
from django.utils.deprecation import RemovedInNextVersionWarning
from django.utils.encoding import force_text
from django.utils.module_loading import import_string
from django.views.debug import ExceptionReporter, get_exception_reporter_filter


class SESHandler(logging.Handler):
    """
    An exception log handler that emails the administrator using amazing SES
    """
    
    def __init__(self, include_html=True, email_backend=None):
        logging.Handler.__init__(self)
        self.include_html = include_html
        self.email_backend = email_backend

    def emit(self, record):
        try:
            request = record.request
            subject = '%s (%s IP): %s' % (
                record.levelname,
                ('internal' if request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS
                 else 'EXTERNAL'),
                record.getMessage()
            )
            filter = get_exception_reporter_filter(request)
            request_repr = '\n{0}'.format(force_text(filter.get_request_repr(request)))
        except Exception:
            subject = '%s: %s' % (
                record.levelname,
                record.getMessage()
            )
            request = None
            request_repr = "unavailable"
        subject = self.format_subject(subject)

        if record.exc_info:
            exc_info = record.exc_info
        else:
            exc_info = (None, record.getMessage(), None)

        message = "%s\n\nRequest repr(): %s" % (self.format(record), request_repr)
        reporter = ExceptionReporter(request, is_email=True, *exc_info)
        html_message = reporter.get_traceback_html() if self.include_html else None
        conn = self.connection()
        conn.send_email('system@dellarobbiathailand.com', 
                        subject,
                        html_message,
                        ['charliep@dellarobbiathailand.com'],
                        format='html')

    def connection(self):
        return boto.ses.connect_to_region('us-east-1')


    def format_subject(self, subject):
        """
        Escape CR and LF characters, and limit length.
        RFC 2822's hard limit is 998 characters per line. So, minus "Subject: "
        the actual subject must be no longer than 989 characters.
        """
        formatted_subject = subject.replace('\n', '\\n').replace('\r', '\\r')
        return formatted_subject[:989]