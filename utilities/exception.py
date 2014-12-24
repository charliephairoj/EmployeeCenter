import logging

from rest_framework.views import exception_handler


logger = logging.getLogger(__name__)


def customer_exception_handler(exc):
    logger.error(exc)
    return exception_handler(exc)

