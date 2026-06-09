from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from production.models import (
    ProductionOrder,
    ProductionOrderStep,
)
from production.services.orders import start_production_order
from production.serializers.detail import (
    ProductionOrderDetailSerializer,
)
from production.serializers.schedule import (
    UpdateProductionOrderStepsScheduleSerializer,
)
from production.services.detail import (
    build_production_order_detail,
)
from production.services.schedule import (
    update_production_order_steps_schedule,
)
from production.services.material_snapshot_report import (
    build_production_order_material_snapshot_report,
    build_production_order_material_snapshot_summary,
)


class StartProductionOrderSerializer(serializers.Serializer):
    serial_number = serializers.CharField(
        max_length=100,
    )

    use_work_tracking = serializers.BooleanField()

    use_hr_tracking = serializers.BooleanField()

    expected_ready_at = serializers.DateTimeField()

    comment = serializers.CharField(
        required=False,
        allow_blank=True,
    )


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

        serializer = StartProductionOrderSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        result = start_production_order(
            production_order=production_order,
            serial_number=serializer.validated_data["serial_number"],
            use_work_tracking=serializer.validated_data["use_work_tracking"],
            use_hr_tracking=serializer.validated_data["use_hr_tracking"],
            expected_ready_at=serializer.validated_data["expected_ready_at"],
            comment=serializer.validated_data.get("comment", ""),
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

    @action(detail=True, methods=["get"], url_path="detail")
    def detail_view(self, request, pk=None):
        try:
            production_order = (
                ProductionOrder.objects.select_related(
                    "sales_order",
                    "sales_order__organization",
                    "sales_order__product",
                    "sales_order__product__product_family",
                ).prefetch_related(
                    "steps",
                ).get(pk=pk)
            )

            self.check_object_permissions(
                request,
                production_order,
            )

            data = build_production_order_detail(
                production_order=production_order,
            )

            serializer = ProductionOrderDetailSerializer(data)

            return Response(serializer.data)

        except Exception as exc:
            import sys
            import traceback

            print(
                f"ProductionOrder detail failed: {exc}",
                file=sys.stderr,
                flush=True,
            )
            print(
                traceback.format_exc(),
                file=sys.stderr,
                flush=True,
            )

            raise

    @action(detail=True, methods=["get"], url_path="material-snapshot")
    def material_snapshot(self, request, pk=None):
        production_order = self.get_object()

        data = build_production_order_material_snapshot_report(
            production_order=production_order,
        )

        return Response(data)

    @action(
        detail=True,
        methods=["get"],
        url_path="material-snapshot-summary",
    )
    def material_snapshot_summary(self, request, pk=None):
        production_order = self.get_object()

        data = build_production_order_material_snapshot_summary(
            production_order=production_order,
        )

        return Response(data)

    @action(
        detail=True,
        methods=["post"],
        url_path="update-steps-schedule",
    )
    def update_steps_schedule(self, request, pk=None):
        try:
            production_order = self.get_object()

            serializer = UpdateProductionOrderStepsScheduleSerializer(
                data=request.data,
            )
            serializer.is_valid(raise_exception=True)

            result = update_production_order_steps_schedule(
                production_order=production_order,
                steps_data=serializer.validated_data["steps"],
                created_by=request.user,
            )

            data = build_production_order_detail(
                production_order=production_order,
            )

            response_serializer = ProductionOrderDetailSerializer(data)

            return Response({
                "updated_steps": result["updated_steps"],
                "detail": response_serializer.data,
            })

        except Exception as exc:
            import sys
            import traceback

            print(
                f"ProductionOrder update_steps_schedule failed: {exc}",
                file=sys.stderr,
                flush=True,
            )
            print(
                traceback.format_exc(),
                file=sys.stderr,
                flush=True,
            )

            raise