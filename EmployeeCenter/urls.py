from django.conf.urls import *
from django.conf import settings
from tastypie.api import Api
from rest_framework.routers import DefaultRouter

from contacts.api import SupplierResource, CustomerResource
from acknowledgements.api import AcknowledgementResource, ItemResource as AckItemResource
from po.api import PurchaseOrderResource, ItemResource as POItemResource
from shipping.api import ShippingResource
from projects.api import ProjectResource, RoomResource
from supplies.api import SupplyResource, FabricResource, LogResource, SupplyReservationResource
from equipment.api import EquipmentResource
from products.api import ModelResource, ConfigurationResource, UpholsteryResource, TableResource
from administrator.api import UserResource, GroupResource, PermissionResource
from hr.api import EmployeeResource, AttendanceResource

from contacts.views import CustomerViewSet, SupplierViewSet, SupplierList, SupplierDetail
from supplies.views import SupplyList, SupplyDetail, supply_type_list, LogViewSet
from supplies.views import FabricList, FabricDetail
from supplies.views import LogList, LogDetail
from products.views import ConfigurationViewSet, ModelViewSet
from products.views import UpholsteryList, UpholsteryDetail, UpholsteryViewSet
from products.views import TableList, TableDetail
from acknowledgements.views import AcknowledgementList, AcknowledgementDetail
from shipping.views import ShippingList, ShippingDetail
from po.views import PurchaseOrderList, PurchaseOrderDetail
from projects.views import ProjectList, ProjectDetail
from projects.views import RoomList, RoomDetail
from hr.views import EmployeeList, EmployeeDetail
from hr.views import AttendanceList, AttendanceDetail
from administrator.views import UserList, UserDetail
from administrator.views import GroupList, GroupDetail
from administrator.views import PermissionList, PermissionDetail
from equipment.views import EquipmentList, EquipmentDetail


"""
API Section

This area deals with the registration of the 
resources with the api 
"""



router = DefaultRouter()

router.register(r'api/v1/customer', CustomerViewSet)
router.register(r'api/v1/model', ModelViewSet)
router.register(r'api/v1/configuration', ConfigurationViewSet)



#primary login and url routing
urlpatterns = patterns('',
    url(r'^$', 'login.views.app_login'),
    url(r'^login$', 'login.views.app_login'),
    url(r'^logout$', 'login.views.logout'),
    url(r'^api/v1/current_user$', 'administrator.views.current_user'),
    url(r'^/api/v1/current_user$', 'administrator.views.current_user'),
    url(r'^/api/v1/change_password', 'auth.views.change_password'),
    url(r'^/api/v1/change_password', 'auth.views.change_password'),
    
    url(r'^', include(router.urls)),
    
    url(r'^api/v1/supplier/$', SupplierList.as_view()),
    url(r'^api/v1/supplier/(?P<pk>[0-9]+)/$', SupplierDetail.as_view()),
    url(r'^api/v1/supply/$', SupplyList.as_view()),
    url(r'^api/v1/supply/(?P<pk>[0-9]+)/$', SupplyDetail.as_view()),
    url(r'^api/v1/supply/type/$', supply_type_list),
    url(r'^api/v1/supply/type$', supply_type_list),
    url(r'^api/v1/fabric/$', FabricList.as_view()),
    url(r'^api/v1/fabric/(?P<pk>[0-9]+)/$', FabricDetail.as_view()),
    url(r'^api/v1/upholstery/$', UpholsteryList.as_view()),
    url(r'^api/v1/upholstery/(?P<pk>[0-9]+)/$', UpholsteryDetail.as_view()),
    url(r'^api/v1/table/$', TableList.as_view()),
    url(r'^api/v1/table/(?P<pk>[0-9]+)/$', TableDetail.as_view()),
    url(r'^api/v1/acknowledgement/$', AcknowledgementList.as_view()),
    url(r'^api/v1/acknowledgement/(?P<pk>[0-9]+)/$', AcknowledgementDetail.as_view()),
    url(r'^api/v1/shipping/$', ShippingList.as_view()),
    url(r'^api/v1/shipping/(?P<pk>[0-9]+)/$', ShippingDetail.as_view()),
    url(r'^api/v1/purchase-order/$', PurchaseOrderList.as_view()),
    url(r'^api/v1/purchase-order/(?P<pk>[0-9]+)/$', PurchaseOrderDetail.as_view()),
    url(r'^api/v1/employee/$', EmployeeList.as_view()),
    url(r'^api/v1/employee/(?P<pk>[0-9]+)/$', EmployeeDetail.as_view()),
    url(r'^api/v1/attendance/$', AttendanceList.as_view()),
    url(r'^api/v1/attendance/(?P<pk>[0-9]+)/$', AttendanceDetail.as_view()),
    url(r'^api/v1/project/$', ProjectList.as_view()),
    url(r'^api/v1/project/(?P<pk>[0-9]+)/$', ProjectDetail.as_view()),
    url(r'^api/v1/room/$', RoomList.as_view()),
    url(r'^api/v1/room/(?P<pk>[0-9]+)/$', RoomDetail.as_view()),
    url(r'^api/v1/user/$', UserList.as_view()),
    url(r'^api/v1/user/(?P<pk>[0-9]+)/$', UserDetail.as_view()),
    url(r'^api/v1/group/$', GroupList.as_view()),
    url(r'^api/v1/group/(?P<pk>[0-9]+)/$', GroupDetail.as_view()),
    url(r'^api/v1/permission/$', PermissionList.as_view()),
    url(r'^api/v1/permission/(?P<pk>[0-9]+)/$', PermissionDetail.as_view()),
    url(r'^api/v1/equipment/$', EquipmentList.as_view()),
    url(r'^api/v1/equipment/(?P<pk>[0-9]+)/$', EquipmentDetail.as_view()),
    url(r'^api/v1/log/$', LogList.as_view()),
    url(r'^api/v1/log/(?P<pk>[0-9]+)/$', LogDetail.as_view())
)



urlpatterns += patterns('acknowledgements.views',
    #url(r'^acknowledgement$', 'acknowledgement'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)$', 'acknowledgement'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)/pdf$', 'pdf'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)/log$', 'log'),
    #url(r'^api/v1/acknowledgement/schedule$', 'schedule'),
    url(r'/api/v1/acknowledgement/item/image$', 'acknowledgement_item_image'),
    url(r'^api/v1/acknowledgement/item/image$', 'acknowledgement_item_image'),
    url(r'/api/v1/acknowledgement/item/image/$', 'acknowledgement_item_image'),
    url(r'^api/v1/acknowledgement/item/image/$', 'acknowledgement_item_image')
    
    #url(r'^acknowledgement/item$', 'item'),
    #url(r'^acknowledgement/item/(?P<ack_item_id>\d+)$', 'item')
)

urlpatterns += patterns('products.views',
    #url(r'^acknowledgement$', 'acknowledgement'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)$', 'acknowledgement'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)/pdf$', 'pdf'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)/log$', 'log'),
    #url(r'^api/v1/acknowledgement/schedule$', 'schedule'),
    url(r'/api/v1/upholstery/image$', 'product_image'),
    url(r'^api/v1/upholstery/image/$', 'product_image')
   
    
    #url(r'^acknowledgement/item$', 'item'),
    #url(r'^acknowledgement/item/(?P<ack_item_id>\d+)$', 'item')
)

urlpatterns += patterns('supplies.views',
    #url(r'^acknowledgement$', 'acknowledgement'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)$', 'acknowledgement'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)/pdf$', 'pdf'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)/log$', 'log'),
    #url(r'^api/v1/acknowledgement/schedule$', 'schedule'),
    url(r'^/api/v1/supply/image/$', 'supply_image'),
    url(r'^api/v1/supply/image/$', 'supply_image')
    
    #url(r'^acknowledgement/item$', 'item'),
    #url(r'^acknowledgement/item/(?P<ack_item_id>\d+)$', 'item')
)

urlpatterns += patterns('hr.views',
    #url(r'^acknowledgement$', 'acknowledgement'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)$', 'acknowledgement'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)/pdf$', 'pdf'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)/log$', 'log'),
    #url(r'^api/v1/acknowledgement/schedule$', 'schedule'),
    url(r'^/api/v1/employee/image/$', 'employee_image'),
    url(r'^api/v1/employee/image/$', 'employee_image')
    
    #url(r'^acknowledgement/item$', 'item'),
    #url(r'^acknowledgement/item/(?P<ack_item_id>\d+)$', 'item')
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