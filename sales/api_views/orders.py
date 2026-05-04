from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from sales.models import SalesOrder
from sales.serializers import (
    SalesOrderSerializer,
    CreateSalesOrderSerializer,
)
from sales.services.orders import create_sales_order


class SalesOrderViewSet(ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]

    queryset = SalesOrder.objects.select_related(
        "organization",
        "product",
        "created_by",
    ).prefetch_related(
        "components",
        "components__inv_item",
    ).order_by("-created_at", "-id")

    serializer_class = SalesOrderSerializer
    permission_classes = [DjangoModelPermissions]

    def create(self, request, *args, **kwargs):
        serializer = CreateSalesOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sales_order = create_sales_order(
            organization=serializer.validated_data["organization"],
            product=serializer.validated_data["product"],
            created_by=request.user if request.user.is_authenticated else None,
            comment=serializer.validated_data.get("comment", ""),
        )

        sales_order = self.get_queryset().get(pk=sales_order.pk)

        return Response(self.get_serializer(sales_order).data)