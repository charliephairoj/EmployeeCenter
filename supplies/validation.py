"""
Validation classes for supplies
"""
from decimal import Decimal
import logging

from tastypie.validation import Validation


logger = logging.getLogger(__name__)


class SupplyValidation(Validation):
    
    def is_valid(self, bundle, request=None):
        """
        Validates the data to be applied to the supply model
        """
        errors = {}
        
        #Validate the description is not an empty string
        #and that it is submitted
        try:
            if bundle.data['description'].strip() == '':
                errors['description'] = "The description cannot be an empty string"
        except KeyError:
            errors['description'] = "Expecting a description for this supply"
            
        #Validates that the dimensions are present and an integer
        dimensions = ['width']#, 'height', 'depth']
        for dimension in dimensions:
            try: 
                Decimal(bundle.data[dimension])
            except KeyError:
                errors[dimension] = "Expecting a {0} for the supply".format(dimension)
            except ValueError:
                errors[dimension] = "Expecting an integer for the {0}".format(dimension)
                
        #Validates that the quantity is present and that it is an integer
        try:
            pass#Decimal(bundle.data['quantity'])
        except KeyError:
            errors['quantity'] = "Expecting a current quantity for this item"
        except ValueError:
            errors['quantity'] = "Expecting an integer for the quantity"

            #Validates the quantity type
        #if "quantity_type" not in bundle.data:
        #    errors['quantity_type'] = "Expecting an type to meausre the supply's quantity"
        return errors
            

class FabricValidation(SupplyValidation):
    
    def is_valid(self, bundle, request=None):
        """
        Validates the data to be applied to the fabric model
        """
        errors = super(FabricValidation, self).is_valid(bundle, request)
        
        try:
            if bundle.data['color'].strip() == "":
                errors['color'] = "The color cannot be an empty string."
        except KeyError:
            errors["color"] = "Expecting a color for this fabric."
            
        try:
            if bundle.data['pattern'].strip() == '':
                errors['pattern'] = "The pattern cannot be an empty string"
        except KeyError:
            errors['pattern'] = "Expecting a pattern for this fabric"

        return errors