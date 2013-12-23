from django.conf.urls import *
from django.conf import settings
from tastypie.api import Api

from contacts.api import SupplierResource, CustomerResource
from acknowledgements.api import AcknowledgementResource, ItemResource as AckItemResource
from po.api import PurchaseOrderResource, ItemResource as POItemResource
from shipping.api import ShippingResource
from supplies.api import SupplyResource, FabricResource
from products.api import ModelResource, ConfigurationResource, UpholsteryResource, TableResource
from administrator.api import UserResource, GroupResource, PermissionResource
"""
API Section

This area deals with the registration of the 
resources with the api 
"""
v1_api = Api(api_name='v1')
v1_api.register(SupplierResource())
v1_api.register(CustomerResource())
v1_api.register(AckItemResource())
v1_api.register(AcknowledgementResource())
v1_api.register(PurchaseOrderResource())
v1_api.register(POItemResource())
v1_api.register(ShippingResource())
v1_api.register(SupplyResource())
v1_api.register(FabricResource())
v1_api.register(UserResource())
v1_api.register(GroupResource())
v1_api.register(PermissionResource())

#Products Category
v1_api.register(ModelResource())
v1_api.register(ConfigurationResource())
v1_api.register(UpholsteryResource())
v1_api.register(TableResource())



#primary login and url routing
urlpatterns = patterns('',
    url(r'^$', 'login.views.app_login'),
    url(r'^login$', 'login.views.app_login'),
    url(r'^logout$', 'login.views.logout'),
    url(r'^api/v1/current_user$', 'auth.views.current_user'),
    url(r'^/api/v1/current_user$', 'auth.views.current_user')
)



#URLS for Acknowledgement

urlpatterns += patterns('acknowledgements.views',
    #url(r'^acknowledgement$', 'acknowledgement'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)$', 'acknowledgement'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)/pdf$', 'pdf'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)/log$', 'log'),
    url(r'/api/v1/acknowledgement/item/image$', 'acknowledgement_item_image'),
    url(r'^api/v1/acknowledgement/item/image$', 'acknowledgement_item_image')
    #url(r'^acknowledgement/item$', 'item'),
    #url(r'^acknowledgement/item/(?P<ack_item_id>\d+)$', 'item')
)

#URL settings for supplies
"""
urlpatterns += patterns('supplies.views',
    #url(r'^supply$', 'supply'),
    #url(r'^supply/(?P<supply_id>\d+)$', 'supply'),
    #url(r'^supply/(?P<supply_id>\d+)$', 'fabric'),
    #url(r'^supply/(?P<supply_id>\d+)/reserve$', 'reserve'),
    #url(r'^supply/(?P<supply_id>\d+)/add$', 'add'),
    #url(r'^supply/(?P<supply_id>\d+)/subtract$', 'subtract'),
    #url(r'^supply/(?P<supply_id>\d+)/reset$', 'reset'),
    #url(r'^supply/(?P<supply_id>\d+)/log$', 'supply_log'),
    url(r'^/api/v1/supply/(?P<supply_id>\d+)/image$', 'supply_image'),
    url(r'^/api/v1/supply/image$', 'supply_image'),
    url(r'^api/v1/supply/image$', 'supply_image'),
)"""

urlpatterns += patterns('products.views',
    url(r'^api/v1/model/image$', 'model_image'),
    
    url(r'^api/v1/upholstery/image$', 'upholstery_image'),
    url(r'^/api/v1/upholstery/image$', 'upholstery_image'),
    
    url(r'^api/v1/table/image$', 'upholstery_image'),
  
)

urlpatterns += patterns('',
    (r'^api/', include(v1_api.urls))
)

urlpatterns += patterns('',
    url(r'^(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.STATIC_ROOT})
)


"""
#Public views
urlpatterns += patterns('products.views',
    url(r'^public/upholstery', 'upholstery')
)

#primary login and url routing
urlpatterns += patterns('login.views',
    url(r'^$', 'app_login'),
    url(r'^main$', 'main'),
    url(r'^login$', 'app_login'),
    url(r'^auth$', 'auth_flow'),
    url(r'^logout$', 'logout')
)

#creates the user profile for client side use
urlpatterns += patterns('auth.views',
    url(r'^auth_service$', 'current_user'),
    url(r'^auth_service/change_password$', 'change_password'),
    url(r'^oauth2callback', 'oauth_callback')
)

#Routes for the Library
urlpatterns += patterns('library.views',
    url(r'^library', 'book')
)

urlpatterns += patterns('products.views',
    url(r'^model$', 'model'),
    url(r'^model/image$', 'model_image'),
    url(r'^model/(?P<model_id>\d+)$', 'model'),
    url(r'^configuration$', 'configuration'),
    url(r'^configuration/(?P<config_id>\d+)$', 'configuration'),
    url(r'^upholstery$', 'upholstery'),
    url(r'^upholstery/image$', 'upholstery_image'),
    url(r'^upholstery/(?P<uphol_id>\d+)$', 'upholstery'),
    url(r'^table$', 'table'),
    url(r'^table/image$', 'upholstery_image'),
    url(r'^table/(?P<table_id>\d+)$', 'table'),
    url(r'^rug$', 'rug'),
    url(r'^rug/(?P<rug_id>\d+)$', 'rug'),
)

urlpatterns += patterns('contacts.views',
    url(r'^contact', 'contact'),
    url(r'^customer$', 'customer'),
    url(r'^customer/(?P<customer_id>\d+)$', 'customer'),
    url(r'^supplier$', 'supplier'),
    url(r'^supplier/(?P<supplier_id>\d+)$', 'supplier'),
    url(r'^supplier_contact$', 'supplierContact'),
    url(r'^supplier_contact/(?P<supplier_contact_id>\d+)$', 'supplierContact'),
)

#URL settings for supplies
urlpatterns += patterns('supplies.views',
    url(r'^supply$', 'supply'),
    url(r'^supply/(?P<supply_id>\d+)$', 'supply'),
    url(r'^supply/(?P<supply_id>\d+)$', 'fabric'),
    url(r'^supply/(?P<supply_id>\d+)/reserve$', 'reserve'),
    url(r'^supply/(?P<supply_id>\d+)/add$', 'add'),
    url(r'^supply/(?P<supply_id>\d+)/subtract$', 'subtract'),
    url(r'^supply/(?P<supply_id>\d+)/reset$', 'reset'),
    url(r'^supply/(?P<supply_id>\d+)/log$', 'supply_log'),
    url(r'^supply/(?P<supply_id>\d+)/image$', 'supply_image'),
    url(r'^supply/image$', 'supply_image'),
    url(r'^lumber$', 'lumber'),
    url(r'^lumber/(?P<lumber_id>\d+)$', 'lumber'),
    url(r'^foam$', 'foam'),
    url(r'^foam/(?P<foam_id>\d+)$', 'foam'),
    url(r'^glue$', 'glue'),
    url(r'^glue/(?P<glue_id>\d+)$', 'glue'),
    url(r'^fabric$', 'fabric'),
    url(r'^fabric/(?P<fabric_id>\d+)$', 'fabric'),
    url(r'^fabric/(?P<supply_id>\d+)/reserve$', 'reserve'),
    url(r'^fabric/(?P<supply_id>\d+)/add$', 'add'),
    url(r'^fabric/(?P<supply_id>\d+)/subtract$', 'subtract'),
    url(r'^fabric/(?P<supply_id>\d+)/reset$', 'reset'),
    url(r'^fabric/(?P<supply_id>\d+)/log$', 'supply_log'),
    url(r'^fabric/(?P<fabric_id>\d+)/image$', 'supply_image'),
    
    url(r'^screw$', 'screw'),
    url(r'^screw/(?P<screw_id>\d+)$', 'screw'),

    url(r'^staple$', 'staple'),
    url(r'^staple/(?P<staple_id>\d+)$', 'staple'),

    url(r'^thread$', 'sewing_thread'),
    url(r'^thread/(?P<sewing_thread_id>\d+)$', 'sewing_thread'),

    url(r'^wool$', 'wool'),
    url(r'^wool/(?P<wool_id>\d+)$', 'wool'),

    url(r'^webbing$', 'webbing'),
    url(r'^webbing/(?P<webbing_id>\d+)$', 'webbing'),

    url(r'^zipper$', 'zipper'),
    url(r'^zipper/(?P<zipper_id>\d+)$', 'zipper'),
)

#URLS for Purchase Order

urlpatterns += patterns('po.views',
    url(r'^purchase_order$', 'purchase_order'),
    url(r'^purchase_order/(?P<po_id>\d+)$', 'purchase_order'),
)

#URLS for Acknowledgement

urlpatterns += patterns('acknowledgements.views',
    url(r'^acknowledgement$', 'acknowledgement'),
    url(r'^acknowledgement/(?P<ack_id>\d+)$', 'acknowledgement'),
    url(r'^acknowledgement/(?P<ack_id>\d+)/pdf$', 'pdf'),
    url(r'^acknowledgement/(?P<ack_id>\d+)/log$', 'log'),
    url(r'^acknowledgement/item/image$', 'acknowledgement_item_image'),
    url(r'^acknowledgement/item$', 'item'),
    url(r'^acknowledgement/item/(?P<ack_item_id>\d+)$', 'item')
)

#URLS for Delivery

urlpatterns += patterns('acknowledgements.views',
    url(r'^delivery$', 'delivery'),
)

#URLS for Shipping
urlpatterns += patterns('shipping.views',
    url(r'^shipping$', 'shipping'),
    url(r'^shipping/(?P<shipping_id>\d+)$', 'shipping'),
    url(r'^shipping/(?P<shipping_id>\d+)/pdf$', 'pdf'),
)

#Urls for Accounting
urlpatterns += patterns('accounting.views',
    url(r'^transaction$', 'transaction'),
    url(r'^transaction/(?P<transaction_id>\d+)$', 'transaction'),
)

#Urls for Project
urlpatterns += patterns("projects.views",
    url(r'^project$', 'project'),
    url(r'^project/(?P<project_id>\d+)$', "project"),

    url(r'^project/room$', 'room'),
    url(r'^project/room/image$', 'room_image'),
    url(r'^project/room/(?P<room_id>\d+)$', "room"),

    url(r'^project/item$', 'item'),
    url(r'^project/item/(?P<item_id>\d+)$', "item"),
    url(r'^project/item/schematic(?P<schematic_id>\d+)$', "item_schematic"),
    url(r'^project/item/schematic$', "item_schematic"),
)
#this section deals with the administration routing area

urlpatterns += patterns('administrator.views',
    url(r'^permission$', 'permission'),
    url(r'^group$', 'group'),
    url(r'^group/(?P<group_id>\d+)$', 'group'),
    url(r'^user$', 'user'),
    url(r'^user/(?P<user_id>\d+)$', 'user'),
    url(r'^user/(?P<user_id>\d+)/change_password$', 'password'),
)


urlpatterns += patterns('',
    url(r'^(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.STATIC_ROOT})
)
"""