import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
import logging
from decimal import *
import xlsxwriter
from io import BytesIO
from urllib2 import urlopen

from django.conf import settings
from django.core.exceptions import *

from hr.models import Employee


django.setup()

logger = logging.getLogger(__name__)


def get_image(url):
    return BytesIO(urlopen(url).read())
        
if __name__ == "__main__":

    columns = ['id', 'image', 'name', 'first_name', 'last_name', 'nickname', 'nationality', 'department']
    row = 0
    wb = xlsxwriter.Workbook('test.xlsx')
    ws = wb.add_worksheet()
    
    ws.set_column(0, 7, 20)
    ws.set_column(1,1, 25)
    
    for employee in Employee.objects.all().order_by('id').order_by('image'):
        
        if row == 0:
            title = wb.add_format({'font_size': 14,
                                   'bold': True,
                                   'align': 'center'})
            
            for index, col in enumerate(columns):
                ws.write(row, index, col.capitalize(), title)    
            row +=1 
        
        ws.set_row(row, 100)
            
        for index, col in enumerate(columns):
            if col == 'image':
                if employee.image:
                    try:
                        ws.insert_image('B' + str(row + 1), 
                                        'image.jpeg', 
                                        {'image_data': get_image(employee.image.generate_url()),
                                         'x_scale': 0.25,
                                         'y_scale': 0.25,
                                         'x_offset': 10,
                                         'y_offset': 10,
                                         'positioning': 2})
                    except AttributeError as e:
                        logger.error(e)
                    except Exception as e:
                        ws.write(row, index, "Image not loading")
                else:
                    ws.write(row, index, '')
            else:
                ws.write(row, index, getattr(employee, col))
        row += 1
    
    wb.close()
            