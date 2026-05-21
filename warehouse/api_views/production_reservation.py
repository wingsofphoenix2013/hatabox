from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import ReadOnlyModelViewSet

from warehouse.models import WarehouseProductionReservation
from warehouse.serializers import (
    WarehouseProductionReservationListSerializer,
)


class WarehouseProductionReservationViewSet(ReadOnlyModelViewSet):
    permission_classes = [DjangoModelPermissions]
    serializer_class = WarehouseProductionReservationListSerializer

    queryset = WarehouseProductionReservation.objects.select_related(
        "sales_order",
        "sales_order__organization",
        "sales_order__product",
        "sales_order__product__product_family",
        "sales_order__production_order",
        "production_order_step_component",
        "production_order_step_component__production_order_step",
        "production_order_step_component__production_order_step__source_product_step",
    ).order_by(
        "-created_at",
        "-id",
    )

    def get_queryset(self):
        queryset = self.queryset

        inv_item = self.request.query_params.get("inv_item")
        if inv_item:
            queryset = queryset.filter(
                sales_order_component__inv_item_id=inv_item,
            )

        return queryset