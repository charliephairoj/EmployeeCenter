"""
Validation file for Employees
"""
from tastypie.validation import Validation


class EmployeeValidation(Validation):
    
    def is_valid(self, bundle, request=None):
        """
        Validates the input
        """
        errors = {}
        
        return errors