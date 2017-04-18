from bs4 import BeautifulSoup
from urllib2 import urlopen
import cookielib
import logging
import mechanize


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


if __name__ == '__main__':
    link = 'http://dellarobbiausa.com/mediacenter/index.aspx'
    
    br = mechanize.Browser()
    br.set_handle_robots(False)
    br.addheaders = [('User-agent', 'Firefox')]
    br.open(link)
    
    br.select_form(name='form1')
    br['password'] = 'furniture'
    br['email'] = 'info@dellarobbiausa.com'
    br.submit()
        
    print br.response().read()