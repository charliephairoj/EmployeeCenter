import logging

from rest_framework.views import exception_handler


logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    logger.error(exc)
    return exception_handler(exc, context)

