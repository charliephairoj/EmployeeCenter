from django.conf.urls import patterns, url
from django.conf import settings




#primary login and url routing

urlpatterns = patterns('login.views',
    url(r'^$', 'appLogin'),
    url(r'^main$', 'main'),
    url(r'^login$', 'appLogin'),
    url(r'^test', 'buildMenu')
    
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
  
    url(r'^supply$', 'supply'),
    url(r'^supply/(?P<supplyID>\d+)$', 'supply')
)

urlpatterns += patterns('lumber.views', 
    url(r'^lumber$', 'lumber'),
    url(r'^lumber/(?P<lumberID>\d+)$', 'lumber'),
    
)

urlpatterns += patterns('foam.views', 
    url(r'^foam$', 'foam'),
    url(r'^foam/(?P<foamID>\d+)$', 'foam'),
    
)

urlpatterns += patterns('fabric.views', 
    url(r'^fabric$', 'fabric'),
    url(r'^fabric/(?P<fabricID>\d+)$', 'fabric'),
    
)

urlpatterns += patterns('screw.views', 
    url(r'^screw$', 'screw'),
    url(r'^screw/(?P<screwID>\d+)$', 'screw'),
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

urlpatterns += patterns('',
    url(r'^(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_ROOT})
)



