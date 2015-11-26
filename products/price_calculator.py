"""
Retrieves a list of Orders and products to be shipped 
in the 14 day period starting today, and creates an 
html message. This email message is then sent to 
the email address
"""


import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
from django.conf import settings
import logging
import json
from decimal import Decimal
import re
import csv
from threading import Thread
from time import sleep
import multiprocessing

from supplies.models import Supply
from products.models import Upholstery, Model, Configuration, Supply as ProductSupply


django.setup()


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def update_upholstery(data):
    # Retrieve or create a configuration
    try:
        configuration = Configuration.objects.get(configuration=data['configuration'])
    except Configuration.DoesNotExist as e:
        configuration = Configuration.objects.create(configuration=data['configuration'])
    except KeyError:
        print p
        
    # Retrieve or create a model
    try:
        model = Model.objects.get(model=data['model'])
    except Model.DoesNotExist as e:
        print e
        print p['Model']
        model = Model.objects.create(model=data['model'])
        
    # Retrieve or create a new upholstery
    try:
        uphol = Upholstery.objects.get(model=model, configuration=configuration)
        uphol.description = "{0} {1}".format(model.model, configuration.configuration)
        uphol.save()
    except Upholstery.DoesNotExist as e:
        logger.debug("{0} {1} does not exist".format(model.model, configuration.configuration))
        uphol = Upholstery.objects.create(model=model, configuration=configuration, description="{0} {1}".format(model.model, configuration.configuration))
    
    # If multiple instances, delete all but the oldest one
    except Upholstery.MultipleObjectsReturned as e:
        logger.debug("Too many instances of {0} {1}. Deleting extras.".format(model.model, configuration.configuration))

        uphols = Upholstery.objects.filter(model=model, configuration=configuration).order_by('id')
        uphol = uphols[0]
        for u in uphols[1:]:
            u.delete()
        
    # Loop through all the columns (supplies) 
    for i in data:
        # Check if this column refers to a specific supply by id
        if re.search(':\s?\w+$', i):
            oi = i
            dd = i.split(':')
            i = dd[0].strip()
            s_id = dd[1].strip()
        else:
            oi = i
            dd = i
            i = i
            s_id = i
            
        # Determine if the column is a supply or description of the product
        if i.lower() not in ['model', 'configuration']:
            try:
                try:
                    ps = ProductSupply.objects.get(product=uphol, supply=Supply.objects.get(pk=s_id))
                    ps.description = i
                except ValueError:
                    ps = ProductSupply.objects.get(product=uphol, description=i.lower())
            except ProductSupply.DoesNotExist:
                ps = ProductSupply(product=uphol)
            except ProductSupply.MultipleObjectsReturned as e:
                logger.debug("Too many instances of {0} for {1}. Deleting extras.".format(i.lower(), uphol.description))
                try:
                    supplies = ProductSupply.objects.filter(product=uphol, supply=Supply.objects.get(pk=s_id)).order_by('id')
                except ValueError:
                    supplies = ProductSupply.objects.filter(product=uphol, description=i.lower()).order_by('id')
                
                ps = supplies[0]
                for s in supplies[1:]:
                    s.delete()
                
            try:
                ps.supply = Supply.objects.get(pk=s_id)
            except ValueError as e:
                pass
            
            try:
                if re.search('qty:\d+', data[oi]):
                    ps.quantity = Decimal(data[oi].split(':')[1].strip())
                else:
                    ps.cost = Decimal(data[oi].replace(',', '') or 0)
            except KeyError:
                pass
            
            ps.description = i
            ps.save()
    
    uphol.calculate_supply_quantities()
    if not uphol.prices.all().exists():
        uphol.calculate_prices(apply_prices=True)
    
    
if __name__ == "__main__":
    

    data = []
    models = {}
    
    with open('product_supply_revised.csv') as file:
        rows = csv.reader(file)
        header = {}
        
        for index, row in enumerate(rows):
            
            if index == 0:
                for i, col in enumerate(row):
                    header[i] = col
            elif row[2] != None and row[2]:
                
                p = {'model': row[0],
                     'configuration': row[1]}
                     
                for i, col in enumerate(row):
                    if i > 1:
                        if row[i] != None and row[i] and header[i].strip().lower() not in ['labor total', 'manufacture total', 'overhead', '50% profit', '30% profit', 'retail']:
                            p[header[i].lower()] = col
                       
                data.append(p)
                
    cpu_count = multiprocessing.cpu_count()
    logger.debug('There are {0} cores'.format(cpu_count))
    
    for index, p in enumerate(data):
        try:
            models[p['model']].append(p['configuration'])
        except KeyError:
            models[p['model']] = [p['configuration']]
                
        if (index + 1) % cpu_count == 0:
            sleep(5)
            
        t = Thread(target=update_upholstery, args=(p, ))
        t.start()
        
    for model in models:
        for config in models[model]:
            pass#logger.debug('{0} {1}'.format(model, config))
            
        bad_uphols = Upholstery.objects.filter(model__model__istartswith=model).exclude(configuration__configuration__in=models[model])
        for u in bad_uphols:
            u.delete()
            logger.debug(u.description)
        

        
        
        
        
        
        