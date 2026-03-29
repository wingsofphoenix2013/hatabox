from django.contrib import admin
from django.urls import path, include

from rest_framework.routers import DefaultRouter

from inventory.api_views import InvUnitViewSet, InvItemCategoryViewSet, InvItemViewSet
from vendors.api_views import VendorViewSet
from orders.api_views import ExternalOrderViewSet, ExternalOrderItemViewSet
from reference.api_views import ExternalOrderStatusViewSet, ExternalOrderPaymentStatusViewSet


router = DefaultRouter()
router.register("units", InvUnitViewSet)
router.register("categories", InvItemCategoryViewSet)
router.register("items", InvItemViewSet)
router.register("vendors", VendorViewSet)
router.register("orders", ExternalOrderViewSet)
router.register("order-items", ExternalOrderItemViewSet)
router.register("order-statuses", ExternalOrderStatusViewSet)
router.register("payment-statuses", ExternalOrderPaymentStatusViewSet)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
]