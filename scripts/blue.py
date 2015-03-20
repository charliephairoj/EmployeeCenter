import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
from django.conf import settings
from django.core.exceptions import *
from decimal import *
import csv
from glob import glob

from contacts.models import Supplier
from supplies.models import Supply, Product


django.setup()


def work():
    data = []
    review = []
    supplier = Supplier.objects.get(name__icontains="blue international")
    with open("/Users/Charlie/Sites/employee/backend/blue-inter.csv", 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            data.append({'reference': row[0],
                         'description': row[1],
                         'cost': row[2],
                         'units': row[3]})
                             
    for index, d in enumerate(data):
        for key in d.keys():
                try:
                    d[key] = d[key].encode('utf-8')
                except UnicodeDecodeError as e:
                    pass
                    
                if key == "cost":
                    try:
                        d[key] = Decimal(d[key].replace(',', ''))
                    except InvalidOperation as e:
                        review.append(data.pop(index))
                        
                if key == "units":
                    if not d[key]:
                        review.append(data.pop(index))

    for index, d in enumerate(data):
        try:
            try:
                supply = Supply.objects.get(description=d['description'])
            except Supply.DoesNotExist:
                supply = Supply()
        
            supply.description = d['description']
            supply.units = d['units']
            supply.full_clean()
            supply.save()
        
        
            try:
                product = Product.objects.get(supply=supply)
            except Product.DoesNotExist:
                product = Product(supply=supply, supplier=supplier)
            
            product.supplier = supplier
            product.supply = supply
            product.reference = d['reference']
            product.cost = d['cost']
            product.purchasing_units = d['units']
            product.full_clean()
            product.save()
            
        except ValidationError as e:
            print e
            review.append(data.pop(index))
            
        assert Supply.objects.filter(description=d['description']).count() == 1
        
    with open('blue-inter-review.csv', 'w') as f:
        fieldnames = ['reference', 'description', 'cost', 'units']
        writer = csv.DictWriter(f)
        writer.write_header()
        for d in review:
            writer.writerow(d)
        
    assert supplier.supplies.all().count() == len(data)
        
    
if __name__ == "__main__":
    work()