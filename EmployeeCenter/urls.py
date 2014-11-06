from django.conf.urls import *
from django.conf import settings
from tastypie.api import Api
from rest_framework import routers
from rest_framework import mixins

from acknowledgements.views import AcknowledgementViewSet, AcknowledgementItemViewSet
from contacts.views import CustomerViewSet, SupplierViewSet
from supplies.views import SupplyViewSet, FabricViewSet, LogViewSet


router = routers.DefaultRouter()
router.register(r'acknowledgement', AcknowledgementViewSet)
router.register(r'acknowledgement-item', AcknowledgementItemViewSet)

router.register(r'customer', CustomerViewSet)
router.register(r'supplier', SupplierViewSet)

router.register(r'supply', SupplyViewSet)
router.register(r'fabric', FabricViewSet)
router.register(r'log', LogViewSet)


urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]



