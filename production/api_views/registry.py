from django.db import models
from django.db.models import Prefetch
from django.utils import timezone

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from production.models import (
    ProductionOrder,
    ProductionOrderStep,
)
from production.serializers.registry import (
    ProductionOrderRegistrySerializer,
)
from warehouse.models import WarehouseProductionMovement


class ProductionOrderRegistryViewSet(ViewSet):
    permission_classes = [DjangoModelPermissions]

    queryset = ProductionOrder.objects.all()

    def list(self, request):
        production_orders = (
            ProductionOrder.objects.select_related(
                "sales_order",
                "sales_order__organization",
                "sales_order__product",
                "sales_order__product__product_family",
            ).filter(
                status__in=[
                    ProductionOrder.Status.IN_PROGRESS,
                    ProductionOrder.Status.READY,
                ]
            ).prefetch_related(
                Prefetch(
                    "steps",
                    queryset=ProductionOrderStep.objects.order_by(
                        "sequence_number",
                        "id",
                    ),
                ),
            ).order_by(
                "-sales_order__created_at",
                "-id",
            )
        )

        production_order_status = request.query_params.getlist(
            "production_order_status"
        )
        if production_order_status:
            production_orders = production_orders.filter(
                status__in=production_order_status,
            )

        sales_order_created_at_from = request.query_params.get(
            "sales_order_created_at_from"
        )
        if sales_order_created_at_from:
            production_orders = production_orders.filter(
                sales_order__created_at__gte=sales_order_created_at_from,
            )

        sales_order_created_at_to = request.query_params.get(
            "sales_order_created_at_to"
        )
        if sales_order_created_at_to:
            production_orders = production_orders.filter(
                sales_order__created_at__lte=sales_order_created_at_to,
            )

        search = request.query_params.get("search")
        if search:
            production_orders = production_orders.filter(
                models.Q(sales_order__organization__name__icontains=search)
                | models.Q(serial_number__icontains=search)
                | models.Q(
                    sales_order__product__product_family__name__icontains=search
                )
            )

        rows = []

        now = timezone.now()

        for production_order in production_orders:
            current_step = None

            if production_order.status != ProductionOrder.Status.READY:
                in_progress_step = next(
                    (
                        step
                        for step in production_order.steps.all()
                        if step.status == ProductionOrderStep.Status.IN_PROGRESS
                    ),
                    None,
                )

                if in_progress_step is not None:
                    current_step = in_progress_step
                else:
                    current_step = next(
                        (
                            step
                            for step in production_order.steps.all()
                            if step.status == ProductionOrderStep.Status.CONFIRMED
                        ),
                        None,
                    )

            movement_executed = False

            if current_step is not None:
                movement_executed = WarehouseProductionMovement.objects.filter(
                    production_order_step=current_step,
                    status=WarehouseProductionMovement.Status.EXECUTED,
                ).exists()

            expected_finished_at = (
                current_step.expected_finished_at
                if current_step
                else None
            )

            is_overdue = (
                expected_finished_at is not None
                and expected_finished_at < now
            )

            days_left = None

            if expected_finished_at is not None:
                days_left = (
                    expected_finished_at.date()
                    - now.date()
                ).days

            rows.append({
                "sales_order_created_at": (
                    production_order.sales_order.created_at
                ),

                "sales_order": production_order.sales_order_id,

                "production_order": production_order.id,
                "production_order_status": production_order.status,

                "organization": (
                    production_order.sales_order.organization_id
                ),
                "organization_name": (
                    production_order.sales_order.organization.name
                ),

                "product": (
                    production_order.sales_order.product_id
                ),
                "product_code": (
                    production_order.sales_order.product.code
                ),

                "product_family": (
                    production_order.sales_order.product.product_family_id
                ),
                "product_family_name": (
                    production_order.sales_order.product.product_family.name
                ),

                "serial_number": production_order.serial_number,

                "current_step": (
                    current_step.source_product_step_id
                    if current_step
                    else None
                ),
                "current_production_order_step": (
                    current_step.id
                    if current_step
                    else None
                ),
                "current_step_name": (
                    current_step.name
                    if current_step
                    else None
                ),
                "current_step_status": (
                    current_step.status
                    if current_step
                    else None
                ),
                "current_step_sequence_number": (
                    current_step.sequence_number
                    if current_step
                    else None
                ),

                "current_step_components_transferred": (
                    movement_executed
                ),

                "current_step_expected_finished_at": (
                    expected_finished_at
                ),
                "current_step_is_overdue": is_overdue,
                "current_step_days_left": days_left,
            })

        current_step = request.query_params.get("current_step")
        if current_step:
            rows = [
                row
                for row in rows
                if row["current_step"] == int(current_step)
            ]

        current_step_components_transferred = request.query_params.get(
            "current_step_components_transferred"
        )
        if current_step_components_transferred is not None:
            transferred_value = (
                current_step_components_transferred.lower() == "true"
            )

            rows = [
                row
                for row in rows
                if (
                    row["current_step_components_transferred"]
                    == transferred_value
                )
            ]

        current_step_is_overdue = request.query_params.get(
            "current_step_is_overdue"
        )
        if current_step_is_overdue is not None:
            overdue_value = (
                current_step_is_overdue.lower() == "true"
            )

            rows = [
                row
                for row in rows
                if row["current_step_is_overdue"] == overdue_value
            ]

        serializer = ProductionOrderRegistrySerializer(
            rows,
            many=True,
        )

        return Response(serializer.data)