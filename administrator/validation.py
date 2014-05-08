"""
Validation classes for the administrator module
"""
import logging
import re

from tastypie.validation import Validation
from django.contrib.auth.models import User


logger = logging.getLogger(__name__)


class UserValidation(Validation):
    
    def is_valid(self, bundle, request=None):
        """
        Checks the data to be entered in the user
        """
        errors = {}
        #Check that an email is provide and that the format is valid
        try:
            if not re.search(r'\w+\@\w+\.\w+', bundle.data['email']):
                errors["email"] = "{0} is not a valid email address.".format(bundle.data['email'])
        except KeyError:
            errors['email'] = "Expecting an email for this user"
            
        if "username" not in bundle.data:
            errors['username'] = "Missing a username for this user."
            
        if "first_name" not in bundle.data:
            errors['first_name'] = "This user is missing a first name"
            
        if "last_name" not in bundle.data:
            errors['last_name'] = "This user is missing a last name"
        return errors  
        