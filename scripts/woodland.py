import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
from django.conf import settings
from django.core.exceptions import *
from decimal import *
import csv
from glob import glob
import xlrd

from contacts.models import Supplier
from supplies.models import Supply, Product

def lower(s):
    try:
        return s.lower()
    except: 
        return s

def test_row(row):
    test_string = "".join([lower(cell.value) for cell in row])
    try:
        for header in ['ref', 'description', 'unit', 'price']:
            if header not in test_string:
                raise ValueError
                
        return True
    except ValueError:
        return False 
        
def extract():
    filename = glob('/Users/Charlie/Downloads/*Siam*.xlsx')[-1]
    wb = xlrd.open_workbook(filename)
    for index in xrange(0, wb.nsheets):
        sheet = wb.sheet_by_index(index)
        positions = {}
        for i in xrange(0, sheet.nrows):
            row = sheet.row(i)
            if test_row(row):
                for index, cell in enumerate(row):
                    for header in ['ref', 'description', 'unit', 'price']:
                        try:
                            if header in cell.value.lower():
                                positions[header] = index
                        except AttributeError:
                            pass
                

if __name__ == "__main__":
    extract()