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

from supplies.models import Supply
from products.models import Upholstery, Model, Configuration, Supply as ProductSupply


django.setup()


if __name__ == "__main__":
    data = []
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
                        
    for p in data:
        try:
            configuration = Configuration.objects.get(configuration=p['configuration'])
        except Configuration.DoesNotExist as e:
            configuration = Configuration.objects.create(configuration=p['configuration'])
        except KeyError:
            print p
        try:
            model = Model.objects.get(model=p['model'])
        except Model.DoesNotExist as e:
            print e
            print p['Model']
            model = Model.objects.create(model=p['model'])
            
        try:
            uphol = Upholstery.objects.get(model=model, configuration=configuration)
            uphol.description = "{0} {1}".format(model.model, configuration.configuration)
            uphol.save()
        except Upholstery.DoesNotExist as e:
            uphol = Upholstery.objects.create(model=model, configuration=configuration, description="{0} {1}".format(model.model, configuration.configuration))
        
        for i in p:
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
                
            if i.lower() not in ['model', 'configuration']:
                try:
                    try:
                        ps = ProductSupply.objects.get(product=uphol, supply=Supply.objects.get(pk=s_id))
                        ps.description = i
                    except ValueError:
                        ps = ProductSupply.objects.get(product=uphol, description=i.lower())
                except ProductSupply.DoesNotExist:
                    ps = ProductSupply(product=uphol)

                    
                try:
                    ps.supply = Supply.objects.get(pk=s_id)
                    
                except ValueError as e:
                    pass
                
                if re.search('qty:\d+', p[oi]):
                    ps.quantity = Decimal(p[oi].split(':')[1].strip())
                else:
                    ps.cost = Decimal(p[oi].replace(',', '') or 0)
                
                ps.description = i
                ps.save()