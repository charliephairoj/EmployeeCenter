from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from login.views import login
admin.autodiscover()



#primary login and url routing

urlpatterns = patterns('login.views',
    url(r'^$', 'appLogin'),
    url(r'^login$', 'appLogin'),
    
)

urlpatterns += patterns('products.views',
    url(r'^model$', 'model'),
    url(r'^model/(?P<modelID>\d+)$', 'model'),
    url(r'^configuration$', 'configuration'),
    url(r'^configuration/(?P<configID>\d+)$', 'configuration'),
    url(r'^upholstery', 'upholstery'),
    url(r'^upholstery/(?P<upholID>\d+)$', 'upholstery'),
    
)
urlpatterns += patterns('contacts.views',
    #url(r'^contact$', 'contact'),
    #url(r'^contact/(?P<contactID>\d+)$', 'contact'),
    url(r'^supplier$', 'supplier'),
    url(r'^supplier/(?P<supplierID>\d+)$', 'supplier'),  
)

urlpatterns += patterns('supplies.views', 
  
    url(r'^supply', 'supply'),
    url(r'^supply/(?P<supplyID>\d+)$', 'supply')
)

urlpatterns += patterns('lumber.views', 
    url(r'^lumber$', 'lumber'),
    url(r'^lumber/(?P<lumberID>\d+)$', 'lumber'),
    
)

urlpatterns += patterns('wool.views', 
    url(r'^wool$', 'wool'),
    url(r'^wool/(?P<woolID>\d+)$', 'wool'),
)

urlpatterns += patterns('po.views', 
    url(r'^purchase_order$', 'purchaseOrder'),
    url(r'^purchase_order/(?P<poID>\d+)$', 'purchaseOrder'),
   
)

#this section deals with the administration routing area

urlpatterns += patterns('administrator.views', 
    url(r'^permission$', 'permission'),
    url(r'^group$', 'group'),
     url(r'^group/(?P<groupID>\d+)$', 'group'),
    url(r'^user$', 'user')
)
urlpatterns += patterns('wool.views',
    url(r'^test', 'display'),
)
urlpatterns += patterns('',
    url(r'^(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/Users/charliephairojmahakij/Sites/EmployeeCenter[Client]/app'})
)



