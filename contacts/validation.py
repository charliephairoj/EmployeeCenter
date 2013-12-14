"""
Validation Classes for the contacts module
"""
import logging
import re

from tastypie.validation import Validation


logger = logging.getLogger(__name__)


class ContactValidation(Validation):
    def is_valid(self, bundle, request=None):
        """
        Validates the data that to be applied to the model
        """
        errors = {}
            
        #Checks and validates for an email address
        try:
            match = re.search(r'\w+\@\w+\.\w+', bundle.data['email'])
            if not match:
                errors["email"] = "{0} is not a valid email".format(bundle.data['email'])
        except KeyError:
            errors["email"] = "Expecting an email for this contact"
        
        #Checks and validates for a telephone number
        try:
            if bundle.data['telephone'].strip() == '':
                errors["telephone"] = "The telephone number cannot be ''."
        except KeyError:
            errors['telephone'] = "Expecting a telephone number for this contact."
            
        #Checks and validates for a currency within the approved currencies
        approved_currencies = ['thb', 'usd', 'eur']
        try:
            if bundle.data['currency'].lower() not in approved_currencies:
                errors['currency'] = "{0} is not an approved currency".format(bundle.data['currency'])
        except KeyError:
            errors['currency'] = "Expecting a currency for this contact"
            
        return errors
    
    
class CustomerValidation(ContactValidation):
    def is_valid(self, bundle, request=None):
        """
        Validates the data that to be applied to the model
        """
        #Perform checks for the contact attributes
        errors = super(CustomerValidation, self).is_valid(bundle, request)
        
        #Check and validate the first name
        try:
            if bundle.data['first_name'].strip() == "" and bundle.data['name'].strip() == "": 
                errors['first_name'] = "Customer's first name cannot be ''."
        except KeyError:
            errors['first_name'] = "Missing customer's first name."
            
        #Checks that the customer type is submitted and that 
        #it is one of the available types in the system
        approved_types = ['retail', 'dealer']
        try:
            if bundle.data['type'].lower() not in approved_types:
                errors['type'] = "{0} is not an available customer type.".format(bundle.data['type'])
        except KeyError:
            errors['type'] = "Expecting a customer type."
        
        return errors
    
    
class SupplierValidation(ContactValidation):
    def is_valid(self, bundle, request=None):
        """
        Validates the data that is to be applied to the model
        """
        #Performs the checks for the common contact attributes
        errors = super(SupplierValidation, self).is_valid(bundle, request)
        
        #Checks and validates the terms 
        try:
            int(bundle.data['terms'])
        except KeyError:
            errors['terms'] = "Expecting terms for this supplier,"
        except ValueError:
            errors['terms'] = "Expecting an integer for the terms for this supplier."
            
        #Checks that there is a discount provided and that the
        #the discount is an integer
        try:
            int(bundle.data['discount'])
        except KeyError:
            errors['discount'] = "Expecting discount for this supplier,"
        except ValueError:
            errors['discount'] = "Expecting an integer for the discount for this supplier."
            
        return errors