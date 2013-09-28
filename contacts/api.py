"""
API file for contacts
"""
import uuid
import logging

from tastypie import fields
from tastypie.authorization import Authorization
from tastypie.resources import ModelResource

from contacts.models import Customer, Supplier, Address


logger = logging.getLogger(__name__)


class ContactResource(ModelResource):
    
    def _set_address(self, bundle):
        """
        Sets the address for the contact
        """
        if "address" in bundle.data:
            addr = self._get_or_create_address(bundle.data["address"])
            addr.contact = bundle.obj
            addr.save()
        elif "addresses" in bundle.data:
            for addr in bundle.data["addresses"]:
                addr = self._get_or_create_address(addr)
                addr.contact = bundle.obj
                addr.save()
        return bundle
    
    def _get_or_create_address(self, addr_data):
        """
        Gets or creates a new address
        """
        if "id" in addr_data:
            try:
                return Address.objects.get(pk=addr_data["id"])
            except Address.DoesNotExist:
                return Address(**addr_data)
        else:
            return Address(**addr_data)


class CustomerResource(ContactResource):
    class Meta:
        queryset = Customer.objects.all()
        resource_name = 'customer'
        always_return_data = True
        authorization = Authorization()
    
    def obj_create(self, bundle, **kwargs):
        """
        Creating a new customer resource
        """
        try:
            name = "{0} {1}".format(bundle.data["first_name"], 
                                    bundle.data["last_name"])
        except KeyError:
            name = bundle.data["first_name"]
        logger.info("Creating customer: {0}...".format(name))
        bundle = super(CustomerResource, self).obj_create(bundle, **kwargs)
        
        #Set status as a customer
        bundle.obj.is_customer = True
        
        return bundle
    
    def obj_update(self, bundle, **kwargs):
        """
        Update a customer resource
        """
        #Update the resource
        bundle =  super(CustomerResource, self).obj_update(bundle, **kwargs)
        logger.info("Updating customer: {0}...".format(bundle.obj.name))
        return bundle
    
    def obj_delete(self, bundle, **kwargs):
        """
        Deletes a customer resource
        """
        obj = Customer.objects.get(pk=kwargs["pk"])
        logger.info("Deleting customer: {0}".format(obj.name))
        super(CustomerResource, self).obj_delete(bundle, **kwargs)
        
    def hydrate(self, bundle):
        """
        Set other attributes
        """
        #Write the name
        if "first_name" in bundle.data and "last_name" in bundle.data:
            logger.info("Setting name from first and last name...") 
            bundle.obj.name = u"{0} {1}".format(bundle.data["first_name"],
                                                    bundle.data["last_name"])
        
        #Set the address
        bundle = self._set_address(bundle)
        
        bundle.obj.is_customer = True
                
        return bundle
    

class SupplierResource(ContactResource):
    
    class Meta:
        queryset = Supplier.objects.all()
        resource_name = 'supplier'
        always_return_data = True
        authorization = Authorization()
        
    def obj_create(self, bundle, **kwargs):
        """
        Create a supplier resource
        """
        logger.info("Creating supplier: {0}...".format(bundle.data['name']))
        bundle = super(SupplierResource, self).obj_create(bundle, **kwargs)
        
        #Set status as supplier
        bundle.obj.is_supplier = True
        return bundle
    
    def obj_update(self, bundle, **kwargs):
        """
        Update the supplier resource
        """
        bundle = super(SupplierResource, self).obj_update(bundle, **kwargs)
        logger.info("Updating supplier: {0}...".format(bundle.obj.name))
        return bundle
    
    def obj_delete(self, bundle, **kwargs):
        """
        Delete the supplier resource
        """
        obj = Supplier.objects.get(pk=kwargs['pk'])
        logger.info("Deleting supplier: {0}...".format(obj.name))
        return super(SupplierResource, self).obj_delete(bundle, **kwargs)
    
    def hydrate(self, bundle):
        """
        Set other attributes
        """  
        #Set the address
        bundle = self._set_address(bundle)
        
        bundle.obj.is_supplier = True
                
        return bundle
    
        
