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
from PIL import Image
import colorsys

from supplies.models import Fabric


django.setup()

logger = logging.getLogger(__name__)


def get_image(url):
    return BytesIO(urlopen(url).read())
    
    
def average_image_color(image):
    i = image
    h = i.histogram()
 
    # split into red, green, blue
    r = h[0:256]
    g = h[256:256*2]
    b = h[256*2: 256*3]

    # perform the weighted average of each channel:
    # the *index* is the channel value, and the *value* is its weight
    return (
    	sum( i*w for i, w in enumerate(r) ) / sum(r),
    	sum( i*w for i, w in enumerate(g) ) / sum(g),
    	sum( i*w for i, w in enumerate(b) ) / sum(b)
    )
    
    
def convert_to_hsv(x):
    hsv = colorsys.rgb_to_hsv(*x)
    return hsv[0], hsv[1], hsv[2]
    
    
if __name__ == "__main__":

    columns = ['image', 'id', 'pattern', 'color', 'content', 'width', 'quantity', 'supplier']
    row = 0
    wb = xlsxwriter.Workbook('fabrics.xlsx')
    ws = wb.add_worksheet()
    
    ws.set_column(0, 0, 30)
    ws.set_column(1, 1, 10)
    ws.set_column(2, 4, 30)
    ws.set_column(5, 5, 10)
    ws.set_column(7, 7, 30)
    
    col_pixel = 6.5
    row_pixel = 2
    
    format = wb.add_format({'align': 'center',
                            'valign': 'vjustify',
                            'text_wrap': True,
                            'font_size': 14})
    
    fabrics = {}
    colors = []
    sorted_fabrics = []
    no_image = []
    
    for fabric in Fabric.objects.all():
        if fabric.image:
            fabrics[(fabric.red, fabric.blue, fabric.green)] = fabric
            colors.append((fabric.red, fabric.blue, fabric.green))
        else:
            no_image.append(fabric)
            
    colors.sort(key=convert_to_hsv)
    for color in colors:
        sorted_fabrics.append(fabrics[color])
        
    sorted_fabrics += no_image
    for fabric in sorted_fabrics:
                
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
                if fabric.image:
                    
                    try:
                        url = fabric.image.generate_url()
                        img_data = get_image(url)
                        img = Image.open(img_data)
                        rgb = average_image_color(img)
                    
                        width, height = img.size
                        width, height = float(width), float(height)
                        
                        if height / width > (100 * row_pixel) / (30 * col_pixel):
                            if height > 100 * row_pixel:
                                ratio = (100 * row_pixel) / height
                            else:
                                ratio = height / (100 * row_pixel)
                                
                        else: 
                            if width > 30 * col_pixel:
                                ratio = (col_pixel * 30) / width
                            else:
                                ration = width / (30 * col_pixel)
                                
                        ws.insert_image('A' + str(row + 1), 
                                        'image.jpg', 
                                        {'image_data': img_data,
                                         'x_scale': ratio,
                                         'y_scale': ratio,
                                         'x_offset': 10,
                                         'y_offset': 20,
                                         'positioning': 3})
                    except AttributeError as e:
                        logger.error(e)
                    except Exception as e:
                        logger.error(e)
                        ws.write(row, index, "Image not loading")
                else:
                    ws.write(row, index, '')
            elif col == 'supplier':
                try:
                    ws.write(row, index, u"{0}".format(fabric.suppliers.all()[0].name), format)
                except IndexError:
                    ws.write(row, index, '')
            else:
                ws.write(row, index, getattr(fabric, col), format)
        row += 1
    
    wb.close()
            