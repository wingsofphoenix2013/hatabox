from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError

from sales.models import SalesOrder
from sales.serializers import (
    SalesOrderSerializer,
    CreateSalesOrderSerializer,
    UpdateSalesOrderComponentSourceSerializer,
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
        
    @action(detail=True, methods=["post"], url_path="update-component-source")
    def update_component_source(self, request, pk=None):
        sales_order = self.get_object()

        serializer = UpdateSalesOrderComponentSourceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        component_id = serializer.validated_data["component_id"]

        try:
            component = sales_order.components.get(id=component_id)
        except sales_order.components.model.DoesNotExist:
            raise ValidationError("Компонент замовлення не знайдено.")

        component.source_type = serializer.validated_data["source_type"]

        if component.source_type == component.SourceType.DONATED:
            component.source_organization = serializer.validated_data.get("source_organization")
        else:
            component.source_organization = None

        component.save(update_fields=["source_type", "source_organization"])

        sales_order = self.get_queryset().get(pk=sales_order.pk)

        return Response(self.get_serializer(sales_order).data)