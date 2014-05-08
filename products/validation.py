"""
Validation classes for all products
"""
import logging
import decimal

from tastypie.validation import Validation


logger = logging.getLogger(__name__)


class ConfigurationValidation(Validation):
    
    def is_valid(self, bundle, request=None):
        """
        Validates the data for the configuration
        """
        errors = {}
        
        #Checks that there is a description for the configuration
        #that is being created
        if "configuration" not in bundle.data:
            errors['configuration'] = "Missing a description for this configuration"
            
        return errors


class ModelValidation(Validation):
    
    def is_valid(self, bundle, request=None):
        """
        Validates the data that is to be put into
        the model
        """
        errors = {}
        
        #Checks that there is a model number for the new model
        if "model" not in bundle.data:
            errors['model'] = "Missing the model number."
            
        #Checks that a collection is specified for this model
        approved_collections = ['dellarobbia thailand', 'dwell living']
        try:
            if bundle.data['collection'].lower() not in approved_collections:
                errors['collection'] = "{0} is not an available collection.".format(bundle.data['collection'])
        except KeyError:
            errors["collection"] = "Expecting a collection for this model."

        return errors 


class ProductValidation(Validation):
    
    def is_valid(self, bundle, request=None):
        """
        Validates the data to be put into the model
        """
        errors = {}
        
        #Validates the dimensions are integers and that 
        #they have been submitted
        for key in ['width', 'depth', 'height']:
            try:
                int(bundle.data[key])
            except KeyError:
                errors[key] = "Missing {0}".format(key)
            except ValueError:
                errors[key] = "The {0} should be an integer in mm".format(key)
                
        #Checks that the wholesale price is present and greater than 1
        try:
            if decimal.Decimal(bundle.data['wholesale_price']) <= 0:
                errors['wholesale_price'] = "The wholesale price must be greater than 0."
        except KeyError:
            errors['wholesale_price'] = "Expecting a wholesale price."
        except decimal.InvalidOperation:
            errors['wholesale_price'] = "{0} is not a valid price.".format(bundle.data['wholesale_price'])
            
        return errors
    

class UpholsteryValidation(ProductValidation):
    def is_valid(self, bundle, request=None):
        """
        Validates the data to be put into the 
        upholstery model
        """
        errors = super(UpholsteryValidation, self).is_valid(bundle, request)
        
        #Validates that a model id is provided
        try:
            if bundle.data['model']['id'] == "":
                errors['model'] = "The model's id cannot be ''."
        except KeyError:
            errors['model'] = "Expecting a model id."
            
        #Validates that a configuration id is provided
        try:
            if bundle.data['configuration']['id'] == "":
                errors['configuration'] = "The configuration's id cannot be ''."
        except KeyError:
            errors['configuration'] = "Expecting a configuration id."
            
        #Validates the pillows to be added to the data
        pillows_types = ['back', 'corner', 'lumbar', 'accent']
        for pillow_type in pillows_types:
            key = "{0}_pillow".format(pillow_type)
            try:
                int(bundle.data[key])
            except KeyError:
                errors[key] = "Missing {0} pillow quatity".format(pillow_type)
            except ValueError:
                errors[key] = "Expecting an integer for the {0} pillow's quantity".format(pillow_type)
        
        return errors
    

class TableValidation(ProductValidation):
    def is_valid(self, bundle, request=None):
        """
        Validates the data to be put into the 
        table model
        """
        errors = super(TableValidation, self).is_valid(bundle, request)
        
        #Validates that a model id is provided
        try:
            if bundle.data['model']['id'] == "":
                errors['model'] = "The model's id cannot be ''."
        except KeyError:
            errors['model'] = "Expecting a model id."
            
        #Validates that a configuration id is provided
        try:
            if bundle.data['configuration']['id'] == "":
                errors['configuration'] = "The configuration's id cannot be ''."
        except KeyError:
            errors['configuration'] = "Expecting a configuration id."
            
        """
        #validates the finish
        approved_finishes = ['high gloss', 'semi-gloss', 'veneer', 'melamine']
        try:
            if bundle.data['finish'].lower() not in approved_finishes:
                errors['finish'] = "{0} is not an available finish.".format(bundle.data['finish'])
        except KeyError:
            errors['finish'] = "Expecting a finish for this table"
        """
        return errors
