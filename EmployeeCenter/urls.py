#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.conf.urls import *
from django.conf import settings
from rest_framework.routers import DefaultRouter
import debug_toolbar
from django.contrib.staticfiles import views

import login.views
import administrator.views
import auth.views
import products.views
import acknowledgements.views
import ivr.views
from contacts.views import CustomerList, CustomerDetail, SupplierList, SupplierDetail
from supplies.views import SupplyList, SupplyDetail, supply_type_list, LogViewSet
from supplies.views import FabricList, FabricDetail
from supplies.views import LogList, LogDetail
from supplies.views import supply_image, sticker as SupplySticker, fabric_sticker
from products.views import ConfigurationViewSet
from products.views import ModelList, ModelDetail
from products.views import UpholsteryList, UpholsteryDetail, UpholsteryViewSet
from products.views import TableList, TableDetail
from products.views import ProductSupplyList, ProductSupplyDetail
from products.views import product_image, model_public, bed_public
from estimates.views import EstimateList, EstimateDetail
from acknowledgements.views import AcknowledgementList, AcknowledgementDetail
from shipping.views import ShippingList, ShippingDetail
from po.views import PurchaseOrderList, PurchaseOrderDetail
from po.views import purchase_order_approval, purchase_order_stats
from projects.views import ProjectList, ProjectDetail
from projects.views import PhaseViewSet
from projects.views import RoomList, RoomDetail
from projects.views import RoomItemList, RoomItemDetail
from projects.views import PartViewSet
from projects.views import report, phase_report
from projects.views import project_public, project_image
from hr.views import EmployeeList, EmployeeDetail
from hr.views import AttendanceList, AttendanceDetail
from hr.views import ShiftViewSet
from administrator.views import UserList, UserDetail
from administrator.views import LabelList, LabelDetail
from administrator.views import GroupList, GroupDetail
from administrator.views import PermissionList, PermissionDetail, LogList as ALogList, public_email
from equipment.views import EquipmentList, EquipmentDetail, sticker as EquipmentSticker
from hr.views import PayrollList
from hr.views import employee_stats, employee_image, upload_attendance
from deals.views import DealList, DealDetail
from ivr.views import voice, get_token, test, route_call, recording_callback, call_status_update_callback
"""
API Section

This area deals with the registration of the
resources with the api
"""


router = DefaultRouter()

#router.register(r'api/v1/customer', CustomerViewSet)
#router.register(r'api/v1/model', ModelViewSet)
router.register(r'api/v1/configuration', ConfigurationViewSet)
router.register(r'api/v1/phase', PhaseViewSet)
router.register(r'api/v1/project-part', PartViewSet)
router.register(r'api/v1/shift', ShiftViewSet)


#primary login and url routing
urlpatterns = [
    url(r'^__debug__/', include(debug_toolbar.urls)),
    url(r'^$', login.views.app_login),
    url(r'^main$', login.views.main),
    url(r'^password-reset$', login.views.password_reset),
    url(r'^password-reset/$', login.views.password_reset),
    url(r'^login$', login.views.app_login),
    url(r'^oauth2callback$', login.views.auth_return),
    url(r'^logout$', login.views.logout),
    url(r'^api/v1/current_user$', administrator.views.current_user),
    url(r'^api/v1/current_user$', administrator.views.current_user),
    url(r'^api/v1/change_password', administrator.views.change_password),
    url(r'^api/v1/change_password/', administrator.views.change_password),
    url(r'^api/v1/client/log/$', administrator.views.log),
    url(r'^api/v1/email/public/$', administrator.views.public_email),


    url(r'^', include(router.urls)),

    url(r'^api/v1/supplier/$', SupplierList.as_view()),
    url(r'^api/v1/supplier/(?P<pk>[0-9]+)/$', SupplierDetail.as_view()),
    url(r'^api/v1/customer/$', CustomerList.as_view()),
    url(r'^api/v1/customer/(?P<pk>[0-9]+)/$', CustomerDetail.as_view()),
    url(r'^api/v1/supply/$', SupplyList.as_view()),
    url(r'^api/v1/supply/(?P<pk>[0-9]+)/$', SupplyDetail.as_view()),
    url(r'^api/v1/supply/type/$', supply_type_list),
    url(r'^api/v1/supply/type$', supply_type_list),
    url(r'^api/v1/fabric/$', FabricList.as_view()),
    url(r'^api/v1/fabric/(?P<pk>[0-9]+)/$', FabricDetail.as_view()),
    url(r'^api/v1/model/$', ModelList.as_view()),
    url(r'^api/v1/model/(?P<pk>[0-9]+)/$', ModelDetail.as_view()),
    url(r'^api/v1/upholstery/$', UpholsteryList.as_view()),
    url(r'^api/v1/upholstery/(?P<pk>[0-9]+)/$', UpholsteryDetail.as_view()),
    url(r'^api/v1/product/supply/$', ProductSupplyList.as_view()),
    url(r'^api/v1/product/supply/(?P<pk>[0-9]+)/$', ProductSupplyDetail.as_view()),
    url(r'^api/v1/table/$', TableList.as_view()),
    url(r'^api/v1/table/(?P<pk>[0-9]+)/$', TableDetail.as_view()),
    url(r'^api/v1/estimate/$', EstimateList.as_view()),
    url(r'^api/v1/estimate/(?P<pk>[0-9]+)/$', EstimateDetail.as_view()),
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
    url(r'^api/v1/room-item/$', RoomItemList.as_view()),
    url(r'^api/v1/room-item/(?P<pk>[0-9]+)/$', RoomItemDetail.as_view()),
    url(r'^api/v1/label/$', LabelList.as_view()),
    url(r'^api/v1/label/(?P<pk>[0-9]+)/$', LabelDetail.as_view()),
    url(r'^api/v1/user/$', UserList.as_view()),
    url(r'^api/v1/user/(?P<pk>[0-9]+)/$', UserDetail.as_view()),
    url(r'^api/v1/group/$', GroupList.as_view()),
    url(r'^api/v1/group/(?P<pk>[0-9]+)/$', GroupDetail.as_view()),
    url(r'^api/v1/permission/$', PermissionList.as_view()),
    url(r'^api/v1/permission/(?P<pk>[0-9]+)/$', PermissionDetail.as_view()),
    url(r'^api/v1/equipment/$', EquipmentList.as_view()),
    url(r'^api/v1/equipment/(?P<pk>[0-9]+)/$', EquipmentDetail.as_view()),
    url(r'^api/v1/log/$', LogList.as_view()),
    url(r'^api/v1/log/(?P<pk>[0-9]+)/$', LogDetail.as_view()),
    url(r'^api/v1/deal/$', DealList.as_view()),
    url(r'^api/v1/deal/(?P<pk>[0-9]+)/$', DealDetail.as_view()),
    url(r'^api/v1/payroll/$', PayrollList.as_view()),

    url(r'^api/v1/administrator/log/$', ALogList.as_view()),

]


urlpatterns += [
    #url(r'^acknowledgement$', 'acknowledgement'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)$', 'acknowledgement'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)/pdf$', 'pdf'),
    #url(r'^acknowledgement/(?P<ack_id>\d+)/log$', 'log'),
    #url(r'^api/v1/acknowledgement/schedule$', 'schedule'),
    url(r'api/v1/acknowledgement/stats/$', acknowledgements.views.acknowledgement_stats),
    url(r'api/v1/acknowledgement/item/image$', acknowledgements.views.acknowledgement_item_image),
    url(r'^api/v1/acknowledgement/item/image$', acknowledgements.views.acknowledgement_item_image),
    url(r'api/v1/acknowledgement/item/image/$', acknowledgements.views.acknowledgement_item_image),
    url(r'^api/v1/acknowledgement/item/image/$', acknowledgements.views.acknowledgement_item_image),
    url(r'^api/v1/acknowledgement/file/$', acknowledgements.views.acknowledgement_file),
    url(r'^api/v1/acknowledgement/download', acknowledgements.views.acknowledgement_download)

    #url(r'^acknowledgement/item$', 'item'),
    #url(r'^acknowledgement/item/(?P<ack_item_id>\d+)$', 'item')
]

urlpatterns += [
    url(r'api/v1/upholstery/image$', product_image),
    url(r'^api/v1/upholstery/image$', product_image),
    url(r'^api/v1/upholstery/image/$', product_image),
    url(r'^api/v1/upholstery/image/$', product_image),
    url(r'api/v1/model/image$', product_image),
    url(r'^api/v1/model/image$', product_image),
    url(r'^api/v1/model/image/$', product_image),
    url(r'^api/v1/model/image/$', product_image),
    url(r'^api/v1/model/public/$', model_public),
    url(r'^api/v1/bed/public/$', bed_public)

]

urlpatterns += [
    url(r'^api/v1/supply/image/$', supply_image),
    url(r'^api/v1/supply/image/$', supply_image),
    url(r'api/v1/supply/(?P<pk>\d+)/sticker$', SupplySticker),
    url(r'api/v1/supply/(?P<pk>\d+)/sticker/$', SupplySticker),
    url(r'api/v1/fabric/(?P<pk>\d+)/sticker$', fabric_sticker),
    url(r'api/v1/fabric/(?P<pk>\d+)/sticker/$', fabric_sticker),

]

urlpatterns += [
    url(r'api/v1/equipment/(?P<pk>\d+)/sticker$', EquipmentSticker),
    url(r'api/v1/equipment/(?P<pk>\d+)/sticker/$', EquipmentSticker),
]

urlpatterns += [
    url(r'api/v1/purchase-order/approval$', purchase_order_approval),
    url(r'api/v1/purchase-order/approval/$', purchase_order_approval),
    url(r'api/v1/purchase-order/stats$', purchase_order_stats),
    url(r'api/v1/purchase-order/stats/$', purchase_order_stats)
]

urlpatterns += [
    url(r'api/v1/project/(?P<pk>\d+)/report$', report),
    url(r'api/v1/project/(?P<pk>\d+)/report/$', report),
    url(r'api/v1/phase/(?P<pk>\d+)/report$', phase_report),
    url(r'api/v1/phase/(?P<pk>\d+)/report/$', phase_report),
    url(r'^api/v1/project/image/$', project_image),
    url(r'^api/v1/project/public/$', project_public),

]

urlpatterns += [
    url(r'^api/v1/employee/stats/$', employee_stats),
    url(r'^api/v1/employee/image/$', employee_image),
    url(r'^api/v1/employee/attendance/$', upload_attendance)
]


urlpatterns += [
    url(r'^api/v1/ivr/voice/$', voice),
    url(r'^api/v1/ivr/token/$', get_token),
    url(r'^api/v1/ivr/test/$', test),
    url(r'^api/v1/ivr/test/route_call/$', route_call),
    url(r'^api/v1/ivr/status/$', call_status_update_callback),
#    url(r'^api/v1/ivr/status/(?P<pk>[0-9]+)/$', 'call_status_update_callback'),
    url(r'^api/v1/ivr/recording/$', recording_callback),
]


urlpatterns += [
    url(r'^(?P<path>.*)$', views.serve)
]
   # url(r'^(?P<path>.*)$', 'django.views.static.serve',
   #     {'document_root': settings.STATIC_ROOT})


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
