
import os
from EmployeeCenter.settings import *

#AUTH_PROFILE_MODULE = "auth.User"


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(__file__), 'test.db'),

        'TEST': {
            'NAME': 'testdb'
        }

    }
}

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'administrator',
    #'auth',
    'products',
    'contacts',
    'supplies',
    'po',
    'library',
    'acknowledgements',
    'shipping',
    'deliveries',
    'accounting',
    'projects',
    'media',
    'hr',
    'equipment',
    'estimates',
    'deals',
    #'trcloud',
    'rest_framework',
    'ivr',
    #'twilio',
    #'social.apps.django_app.default',
    'corsheaders',
    #'oauth2client',
    'test',
    'invoices'
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