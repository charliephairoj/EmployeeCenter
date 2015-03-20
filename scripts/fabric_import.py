import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
import logging
import re
from decimal import *
import requests

from PIL import Image
from StringIO import StringIO
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.exceptions import *

from contacts.models import Supplier
from supplies.models import Fabric, Product
from media.models import S3Object


django.setup()

logger = logging.getLogger(__name__)
url_base = "http://www.dellarobbiausa.com/mediacenter/"

def extract_image(response):
    return Image.open(StringIO(response.content))
    
def get_text_from_row(row):
    return row.find_all('td')[-1].get_text()
    
def extract_links(page):
    links = page.find_all('a', class_="TxtRed11")
    links = [url_base + link.attrs['href'] for link in links]
    return links
    
def visit_and_extract_fabric_details(session, link):
    r = session.get(link)
    page = BeautifulSoup(r.text)
    image_link = page.find('a', class_='TxtBrown11', href=re.compile('images/fabrics'))
    image_url = image_link.attrs['href']
    data_table = page.find('td', class_='TxtBrown20').parent.parent
    table_rows = data_table.find_all('tr')[2:]
    info = {'pattern': get_text_from_row(table_rows[0]),
            'color': get_text_from_row(table_rows[1]),
            'composition': get_text_from_row(table_rows[2]),
            'handling': get_text_from_row(table_rows[3]),
            'grade': get_text_from_row(table_rows[4]),
            'repeat': get_text_from_row(table_rows[5])}
    try:
        info['image'] = extract_image(session.get(url_base + image_url))
    except Exception as e:
        print url_base + image_url
        print info['pattern'], info['color']
        print link
        #raise e
    
    return info
    
    
if __name__ == "__main__":
    url_base = "http://www.dellarobbiausa.com/mediacenter/"
    email = "info@dellarobbiausa.com"
    password = "furniture"
    url_base = "http://www.dellarobbiausa.com/mediacenter/"
    login_url = "http://www.dellarobbiausa.com/mediacenter/createsession.aspx"
    login_data = {'email': email, 'password': password}
    r = requests.get(login_url)
    login_page = BeautifulSoup(r.text)
    secret_inputs = login_page.find_all(type="hidden")
    
    for input in secret_inputs:
        login_data[input.attrs['id']] = input.attrs['value']
    
    session = requests.Session()
    r = session.post(login_url, data=login_data)
    
    #Set initial page to be used for set up
    page1 = BeautifulSoup(r.text)
    
    #Extract and prepare data for future pages
    page_indexes = [i for i in xrange(0, len(page1.find_all('a', href="#")))]
    fabrics = []
    for index in page_indexes:
        #Get numbered page with list of fabrics
        page_data = {'ds_fabrics_currentPage': index}
        resp = session.get(url_base + "fabrics.aspx?fabric_status=Current", data=page_data)
        page = BeautifulSoup(resp.text)
        links = extract_links(page)
        
        #Extract Fabric details
        for link in links:
            fabric_data = visit_and_extract_fabric_details(session, link)
            fabrics.append(fabric_data)
    
    supplier = Supplier.objects.get(pk=76)
    
    for f in fabrics:
        try:
            fabric = Fabric.objects.get(pattern=f['pattern'], color=f['color'])
        except Fabric.DoesNotExist:
            fabric = Fabric(pattern=f['pattern'], color=f['color'])
        
        fabric.content = f['composition']
        fabric.handling = f['handling']
        fabric.grade = f['grade']
        fabric.repeat = f['repeat']
        fabric.units = 'yd'
        fabric.type = 'fabric'
        fabric.save()
        
        filename = "{0} Col: {1}".format(fabric.pattern, fabric.color)
        fabric.description = filename
        fabric.save()
        
        print fabric.id, fabric.description
        
        try:
            product = Product.objects.get(supply=fabric, supplier=supplier)
        except Product.DoesNotExist:
            product = Product(supply=fabric, supplier=supplier)
            
        product.purchasing_units = 'yd'
        try:
            product.cost = Decimal(fabric.grade) * Decimal('1.10')
        except Exception:
            product.cost = 0
            
        product.save()
        
        if 'image' in f:
            f['image'].save(filename + ".jpg")
            image = S3Object.create(filename + ".jpg", 
                                    "supply/image/{0}-{1}.jpg".format(fabric.pattern, fabric.color),
                                    'media.dellarobbiathailand.com')
            fabric.image = image
            
        fabric.save()
        
 