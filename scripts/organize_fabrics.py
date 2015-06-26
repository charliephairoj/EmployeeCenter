#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Retrieves a list of Orders and products to be shipped 
in the 30 day period starting today, and creates an 
html message. This email message is then sent to 
the email address
"""

import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
sys.path.append('/home/django_worker/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
from decimal import Decimal
from datetime import timedelta, datetime, date
import logging

import boto
from django.template.loader import render_to_string
from django.conf import settings

from django.db.models import Q, Sum
from supplies.models import Fabric, Shelf, Tower


django.setup()


logger = logging.getLogger(__name__)


def sort_fabrics():
    """
    Sorts all the fabrics in the system in to physical shelves, taking into 
    account maximum capacity, proximity grouping by pattern, and checking
    if there is actually quantity before assigning a shelf
    """
    max_shelf_qty = Decimal('240')
    shelves = Shelf.objects.all().order_by('tower', 'name')
    current_shelf_index = 0
    shelf = shelves[current_shelf_index]
    cell_style = """
                 border-bottom:1px solid #595959;
                 border-right:1px solid #595959;
                 padding:1em 0.5em;
                 text-align:center;
                 font-size:1;
                 font-family:Tahoma;
                 max-height:5em;
                 """
    header_cell_style = """
                        border-right:1px solid #595959;
                        border-bottom:1px solid #595959;
                        border-top:1px solid #595959;
                        padding:1em;
                        """
    item_cell_style = """
                      padding:0.75em 0.25em;
                      """
    
    def exceeds_shelf_capacity(shelf, fabric):
        """
        Tests whether adding this fabric to shelf will exceed the shelf's maximum 
        capacity. Returns a boolean based on the result
        """
        shelf_total = Decimal(shelf.fabrics.all().aggregate(Sum('quantity_th'))['quantity_th__sum'] or 0)
        return True if (shelf_total) + fabric.quantity > max_shelf_qty else False
    
    # Reset the shelving arrangements
    Fabric.objects.all().update(shelf=None)
        
    # Loops through the fabrics, organized by patterns so that 
    # similar fabrics by patterns are close to each other
    for fabric in Fabric.objects.filter(item__acknowledgement__time_created__gte=date(2014, 1, 1)).distinct().order_by('pattern', 'color'):
        # Only find a shelf if there is fabric to store
        if fabric.quantity > Decimal('0'):
            if not exceeds_shelf_capacity(shelf, fabric):
                fabric.shelf = shelf
                
            else:
                # Loops through all the previous shelves to look for space
                for past_shelf in shelves[0: current_shelf_index]:
                    if not exceeds_shelf_capacity(past_shelf, fabric):  
                        fabric.shelf = past_shelf
                
                try:
                    if fabric.shelf is None: 
                        current_shelf_index += 1
    
                        try:
                            shelf = shelves[current_shelf_index]
                        except (KeyError, IndexError):
                            pass#raise ValueError("You've run out of space to store fabrics!")
                        
                        fabric.shelf = shelf
                        
                except Exception:
                    current_shelf_index += 1
    
                    try:
                        shelf = shelves[current_shelf_index]
                    except (KeyError, IndexError):
                        pass#raise ValueError("You've run out of space to store fabrics!")
                        
                    fabric.shelf = shelf
                        
            fabric.save()

    
        
    #return self.message
    return render_to_string('fabric_email.html', {'towers': Tower.objects.all().order_by('id'),
                                                  'header_style': header_cell_style,
                                                  'cell_style': cell_style,
                                                  'item_cell_style': item_cell_style})
        
        
# Run the fabric sort function if calling from command line
if __name__ == "__main__":
    
    
    message = sort_fabrics()
    e_conn = boto.ses.connect_to_region('us-east-1')
    e_conn.send_email('noreply@dellarobbiathailand.com',
                      'Fabric Organization',
                      message,
                      ["charliep@dellarobbiathailand.com", "chutima@dellarobbiathailand.com"],
                      format='html')
    