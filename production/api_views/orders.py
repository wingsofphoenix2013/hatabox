from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from production.models import ProductionOrder
from production.services.orders import start_production_order


class ProductionOrderViewSet(ModelViewSet):
    http_method_names = [
        "get",
        "post",
        "head",
        "options",
    ]
    permission_classes = [DjangoModelPermissions]
    queryset = ProductionOrder.objects.select_related(
        "sales_order",
    ).order_by(
        "-created_at",
        "-id",
    )

    def get_serializer_class(self):
        from rest_framework import serializers

        class ProductionOrderSerializer(serializers.ModelSerializer):
            class Meta:
                model = ProductionOrder
                fields = [
                    "id",
                    "sales_order",
                    "status",
                    "serial_number",
                    "use_work_tracking",
                    "use_hr_tracking",
                    "comment",
                    "created_at",
                    "ready_at",
                ]
                read_only_fields = fields

        return ProductionOrderSerializer

    @action(detail=True, methods=["post"], url_path="start")
    def start(self, request, pk=None):
        production_order = self.get_object()

        result = start_production_order(
            production_order=production_order,
            created_by=request.user if request.user.is_authenticated else None,
        )

        production_order = self.get_queryset().get(pk=production_order.pk)

        return Response({
            "production_order": production_order.id,
            "status": production_order.status,
            "sales_order": production_order.sales_order_id,
            "sales_order_status": production_order.sales_order.status,
            "created_movements": result["created_movements"],
        })