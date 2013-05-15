from django.conf.urls import patterns, url
from django.conf import settings


#Public views
urlpatterns = patterns('products.views',
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
    url(r'^fabric/(?P<fabric_id>\d+)/reserve$', 'fabric_reserve'),
    url(r'^fabric/(?P<fabric_id>\d+)/add$', 'fabric_add'),
    url(r'^fabric/(?P<fabric_id>\d+)/subtract$', 'fabric_subtract'),
    url(r'^fabric/(?P<fabric_id>\d+)/reset$', 'fabric_reset'),
    url(r'^fabric/(?P<fabric_id>\d+)/log$', 'fabric_log'),
    url(r'^fabric/(?P<fabric_id>\d+)/image$', 'fabric_image'),
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

#this section deals with the administration routing area

urlpatterns += patterns('administrator.views',
    url(r'^permission$', 'permission'),
    url(r'^group$', 'group'),
    url(r'^group/(?P<group_id>\d+)$', 'group'),
    url(r'^user$', 'user'),
    url(r'^user/(?P<user_id>\d+)$', 'user'),
)

urlpatterns += patterns('',
    url(r'^(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.STATIC_ROOT})
)
