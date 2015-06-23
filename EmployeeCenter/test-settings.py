
from EmployeeCenter.settings import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3'
    }
}

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
    },
    'handlers': {
        
        'console':{
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter':'standard'
        },
        'system_log': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/Users/Charlie/Sites/employee/backend/log.txt',
            'formatter': 'standard'
        },
        'email': {
            'level': 'ERROR',
            'class': 'utilities.log.SESHandler',
            'formatter': 'standard'
        }
    },
    'loggers': {
        '': {
             'handlers': ['console', 'system_log'],
             'level': 'DEBUG',
             'propagate': True
        },
        'django.db.backends': {
            'handlers': [],  # Quiet by default!
            'propagate': False,
            'level':'DEBUG',
        },
    }
}