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
    InvItemOptionsView,
    ProductFamilyViewSet,
    ProductFamilyLibraryViewSet,
    ProductViewSet,
    ProductOptionsView,
    ProductLibraryViewSet,
    ProductStepViewSet,
    ProductStepLibraryViewSet,
    ProductStepItemViewSet,
)

from vendors.api_views import (
    VendorViewSet,
    VendorItemViewSet,
    VendorPaymentDetailsViewSet,
)

from orders.api_views import (
    ExternalOrderViewSet,
    ExternalOrderRegistryViewSet,
    ExternalOrderRegisterLightViewSet,
    ExternalOrderEventViewSet,
    ExternalOrderItemViewSet,
    ExternalPaymentDocumentViewSet,
    ExternalReceiptDocumentViewSet,
    ExternalReceiptItemViewSet,
    TollingOrderViewSet,
    TollingOrderItemViewSet,
    TollingReceiptDocumentViewSet,
    TollingReceiptItemViewSet,
)

from warehouse.api_views import (
    WarehouseLocationViewSet,
    WarehouseStoragePlaceViewSet,
    WarehouseUnitViewSet,
    WarehousePendingIntakeItemViewSet,
    WarehouseTollingPendingIntakeItemViewSet,
    WarehouseStockOverviewViewSet,
    WarehouseStockDetailViewSet,
    MovementPlanViewSet,
    WarehouseSalesOrderAvailabilityViewSet,
    WarehouseShortageOverviewViewSet,
    WarehouseShortageDetailViewSet,
)

from reference.api_views import (
    BrandViewSet,
    CountryViewSet,
    ExternalOrderStatusViewSet,
    ExternalOrderPaymentStatusViewSet,
    TaxTypeViewSet,
)

from organizations.api_views import (
    OrganizationViewSet,
    CommercialOrganizationViewSet,
    MilitaryOrganizationViewSet,
    CharityOrganizationViewSet,
    PersonViewSet,
    OrganizationPositionViewSet,
    OrganizationPersonAssignmentViewSet,
    PeopleDirectoryViewSet,
)

from accounts.views import login_view, me_view
from sales.api_views import SalesOrderViewSet
from production.api_views import ProductionDiaryEntryViewSet


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
router.register("vendor-payment-details", VendorPaymentDetailsViewSet)
router.register("vendor-items", VendorItemViewSet)
router.register("orders", ExternalOrderViewSet)
router.register("orders-registry", ExternalOrderRegistryViewSet, basename="orders-registry")
router.register("orders-register", ExternalOrderRegisterLightViewSet, basename="orders-register")
router.register("order-events", ExternalOrderEventViewSet, basename="order-events")
router.register("order-items", ExternalOrderItemViewSet)
router.register("payment-documents", ExternalPaymentDocumentViewSet)
router.register("receipt-documents", ExternalReceiptDocumentViewSet)
router.register("receipt-items", ExternalReceiptItemViewSet)

router.register("tolling-orders", TollingOrderViewSet)
router.register("tolling-order-items", TollingOrderItemViewSet)
router.register("tolling-receipt-documents", TollingReceiptDocumentViewSet)
router.register("tolling-receipt-items", TollingReceiptItemViewSet)

router.register("tax-types", TaxTypeViewSet)

router.register("organizations", OrganizationViewSet)
router.register("commercial-organizations", CommercialOrganizationViewSet)
router.register("military-organizations", MilitaryOrganizationViewSet)
router.register("charity-organizations", CharityOrganizationViewSet)
router.register("people", PersonViewSet)
router.register("organization-positions", OrganizationPositionViewSet)
router.register("organization-person-assignments", OrganizationPersonAssignmentViewSet)
router.register(
    "people-directory",
    PeopleDirectoryViewSet,
    basename="people-directory",
)

router.register("warehouse-locations", WarehouseLocationViewSet)
router.register("warehouse-storage-places", WarehouseStoragePlaceViewSet)
router.register("warehouse-units", WarehouseUnitViewSet)
router.register("movement-plans", MovementPlanViewSet)
router.register(
    "warehouse-pending-intake-items",
    WarehousePendingIntakeItemViewSet,
    basename="warehouse-pending-intake-item",
)
router.register(
    "warehouse-tolling-pending-intake-items",
    WarehouseTollingPendingIntakeItemViewSet,
    basename="warehouse-tolling-pending-intake-item",
)
router.register(
    "warehouse-stock-overview",
    WarehouseStockOverviewViewSet,
    basename="warehouse-stock-overview",
)
router.register(
    "warehouse-stock-detail",
    WarehouseStockDetailViewSet,
    basename="warehouse-stock-detail",
)

router.register(
    "warehouse-sales-order-availability",
    WarehouseSalesOrderAvailabilityViewSet,
    basename="warehouse-sales-order-availability",
)

router.register(
    "warehouse-shortage-overview",
    WarehouseShortageOverviewViewSet,
    basename="warehouse-shortage-overview",
)

router.register(
    "warehouse-shortage-detail",
    WarehouseShortageDetailViewSet,
    basename="warehouse-shortage-detail",
)
router.register("order-statuses", ExternalOrderStatusViewSet)
router.register("payment-statuses", ExternalOrderPaymentStatusViewSet)
router.register("brands", BrandViewSet)
router.register("countries", CountryViewSet)
router.register("sales-orders", SalesOrderViewSet)
router.register("production-diary-entries", ProductionDiaryEntryViewSet)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/login/", login_view),
    path("api/me/", me_view),
    path("api/csrf/", csrf_view),
    path("api/inventory-item-options/", InvItemOptionsView.as_view()),
    path("api/product-options/", ProductOptionsView.as_view()),
    path("api/", include(router.urls)),
]