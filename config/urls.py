from django.contrib import admin
from django.urls import path, include

from rest_framework.routers import DefaultRouter
from vendors.api_views import VendorViewSet


router = DefaultRouter()
router.register("vendors", VendorViewSet)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
]