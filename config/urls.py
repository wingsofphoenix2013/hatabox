from django.contrib import admin
from django.urls import path, include

from rest_framework.routers import DefaultRouter
from vendors.api_views import VendorViewSet
from orders.api_views import ExternalOrderViewSet


router = DefaultRouter()
router.register("vendors", VendorViewSet)
router.register("orders", ExternalOrderViewSet)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
]