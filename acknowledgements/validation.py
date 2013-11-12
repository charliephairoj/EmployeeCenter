"""
Custom validation files for acknowledgements
"""
import dateutil
import logging

from tastypie.validation import Validation


logger = logging.getLogger(__name__)


class AcknowledgementValidation(Validation):
    
    def is_valid(self, bundle, request=None):
        """
        Validates that the data to be inputted into the model
        is valid
        """
        errors = {}
        
        #Check that there is a delivery date
        #and that the date is a valid format 
        if "delivery_date" in bundle.data:
            try:
                dateutil.parser.parse(bundle.data['delivery_date'])
            except Exception:
                logger.error("Missing delivery date.")
                errors['delivery_date'] = "Not a valid date format."
                
        #Checks that there is a vat and that 
        #it is an integer
        if "vat" in bundle.data:
            try:
                int(bundle.data['vat'])
            except Exception:
                errors["vat"] = "Must be an integer"
        else:
            logger.error("Missing vat.")
            errors['vat'] = "Missing the vat"
            
        #Checks that there is a items section and that is contains an
        #array of objects more than 0
        if "items" in bundle.data:
            if not len(bundle.data['items']) > 0:
                logger.error("No items have been ordered.")
                errors["items"] = "No items have been ordered"
            else:
                try:
                    for item in bundle.data['items']:
                        self._validate_item(item)
                except (ValueError, TypeError) as e:
                    logger.error(e)
                    errors['items'] = e
                    
        else:
            errors['items'] = "No items have been ordered"
            
        return errors
    
    def _validate_item(self, item):
        """
        Validates that a data for an item is complete so that 
        an order can be built
        """
        #Checks that there is an id to find the 
        #corresponding product
        if "id" not in item:
            raise ValueError("Expecting an id for the this item")
        
        
        #Checks that each item has a quantity that is an integer
        try:
            int(item['quantity'])
        except KeyError:
            raise ValueError("Expecting a quantity.")
        except ValueError:
            raise TypeError("Expecting an integer for quantity.")
        
        #If the product is custom size, we check that there
        #is an integer for width, depth and height
        if "is_custom_size" in item:
            if item['is_custom_size']:
                for key in ['width', 'depth', 'height']:
                    try:
                        int(item[key])
                    except Exception:
                        raise TypeError("Expecting a integer for a {0}.".format(key))
        
        #check that if the item has a fabric that there is
        #a fabric id to look up the fabric from the system
        if "fabric" in item:
            if "id" not in item['fabric']:
                raise ValueError("Expecting an id for the fabric.")
            
        #validates pillows if there are any
        try:
            for pillow in item['pillows']:
                self._validate_pillow(pillow)
        except (TypeError, ValueError) as e:
            raise
        except KeyError:
            pass

                
    def _validate_pillow(self, pillow):
        
        #Checks that each pillow as a quantity that is an integer
        try:
            int(pillow['quantity'])
        except KeyError:
            raise ValueError("Expecting a quantity for this pillow.")
        except ValueError:
            raise TypeError("Expecting an integer for the quantity of this pillow.")
        
        try:
            types = ['back', 'accent', 'lumbar', 'corner']
            if pillow['type'].lower() not in types:
                raise ValueError("Expecting type to be either 'back', 'accent', 'lumbar', or 'corner'.")
        except KeyError:
            raise ValueError("Expecting a type for this pillow.") 
                
            
                
                
                
    