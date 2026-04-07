from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token

from rest_framework.routers import DefaultRouter

from inventory.api_views import (
    InvUnitViewSet,
    InvItemCategoryViewSet,
    InvItemViewSet,
    ProductFamilyViewSet,
    ProductFamilyLibraryViewSet,
    ProductViewSet,
    ProductLibraryViewSet,
    ProductStepViewSet,
    ProductStepLibraryViewSet,
    ProductStepItemViewSet,
)
from vendors.api_views import VendorViewSet, VendorItemViewSet

from orders.api_views import (
    ExternalOrderViewSet,
    ExternalOrderItemViewSet,
    ExternalPaymentDocumentViewSet,
    ExternalReceiptDocumentViewSet,
    ExternalReceiptItemViewSet,
)

from reference.api_views import (
    BrandViewSet,
    CountryViewSet,
    ExternalOrderStatusViewSet,
    ExternalOrderPaymentStatusViewSet,
    TaxTypeViewSet,
)
from accounts.views import login_view, me_view


@ensure_csrf_cookie
def csrf_view(request):
    return JsonResponse({
        "csrfToken": get_token(request)
    })


router = DefaultRouter()
router.register("units", InvUnitViewSet)
router.register("categories", InvItemCategoryViewSet)
router.register("items", InvItemViewSet)
router.register("product-families", ProductFamilyViewSet)
router.register("product-family-library", ProductFamilyLibraryViewSet)
router.register("products", ProductViewSet)
router.register("product-library", ProductLibraryViewSet)
router.register("product-steps", ProductStepViewSet)
router.register("product-step-library", ProductStepLibraryViewSet)
router.register("product-step-items", ProductStepItemViewSet)
router.register("vendors", VendorViewSet)
router.register("vendor-items", VendorItemViewSet)
router.register("orders", ExternalOrderViewSet)
router.register("order-items", ExternalOrderItemViewSet)
router.register("tax-types", TaxTypeViewSet)
router.register("payment-documents", ExternalPaymentDocumentViewSet)
router.register("receipt-documents", ExternalReceiptDocumentViewSet)
router.register("receipt-items", ExternalReceiptItemViewSet)
router.register("order-statuses", ExternalOrderStatusViewSet)
router.register("payment-statuses", ExternalOrderPaymentStatusViewSet)
router.register("brands", BrandViewSet)
router.register("countries", CountryViewSet)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/login/", login_view),
    path("api/me/", me_view),
    path("api/csrf/", csrf_view),
    path("api/", include(router.urls)),
]