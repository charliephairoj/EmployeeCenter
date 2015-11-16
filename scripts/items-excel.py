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

from acknowledgements.models import Item


django.setup()

logger = logging.getLogger(__name__)


def get_image(url):
    return BytesIO(urlopen(url).read())
        
if __name__ == "__main__":

    columns = ['acknowledgement.id', 'acknowledgement.remarks', 'id', 'image', 'description', 'comments']
    row = 0
    wb = xlsxwriter.Workbook('test.xlsx')
    ws = wb.add_worksheet()
    
    ws.set_column(0, 0, 15)
    ws.set_column(1, 1, 50)
    ws.set_column(2, 2, 15)
    ws.set_column(3, 3, 100)
    ws.set_column(4, 5, 50)
        
    for item in Item.objects.filter(is_custom_item=True).order_by('-id').order_by('image', 'acknowledgement')[0:500]:
        logger.debug(row + 1)
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
                if item.image:
                    if item.image.key.split('.')[-1] in ['jpeg', 'png', 'jpg']:
                        try:
                            ws.insert_image('D' + str(row + 1), 
                                            'image.jpeg', 
                                            {'image_data': get_image(item.image.generate_url()),
                                             'x_scale': 0.35,
                                             'y_scale': 0.35,
                                             'x_offset': 20,
                                             'y_offset': 30,
                                             'positioning': 1})
                        except AttributeError as e:
                            logger.error(e)
                        except Exception as e:
                            ws.write(row, index, "Image not loading")
                    else:
                        ws.write(row, index, "Image not loading")
                else:
                    ws.write(row, index, '')
            elif 'acknowledgement' in col:
                try:
                    ws.write(row, index, getattr(getattr(item, col.split('.')[0]), col.split('.')[-1]))
                except       Exception:
                    pass
            else:
                ws.write(row, index, getattr(item, col))
        row += 1
    
    wb.close()
            