from rest_framework.exceptions import ValidationError
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from sales.models import SalesOrder

from warehouse.serializers import (
    WarehouseSalesOrderAvailabilitySerializer,
)
from warehouse.services.sales_order_availability import (
    build_sales_order_availability,
)


class WarehouseSalesOrderAvailabilityViewSet(ReadOnlyModelViewSet):
    queryset = SalesOrder.objects.all()
    serializer_class = WarehouseSalesOrderAvailabilitySerializer
    permission_classes = [DjangoModelPermissions]

    def list(self, request, *args, **kwargs):
        raise ValidationError(
            "Цей endpoint підтримує лише detail-запит: /api/warehouse-sales-order-availability/{sales_order_id}/"
        )

    def retrieve(self, request, *args, **kwargs):
        sales_order_id = kwargs["pk"]

        data = build_sales_order_availability(
            sales_order_id=sales_order_id,
        )

        serializer = self.get_serializer(data)

        return Response(serializer.data)