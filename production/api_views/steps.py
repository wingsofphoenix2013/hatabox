from django.db import transaction
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from production.models import ProductionOrderStep
from sales.models import SalesOrderEvent
from sales.services.events import create_sales_order_event
from warehouse.services.production_reservation import (
    reserve_components_for_production_step_confirmation,
)
from warehouse.tasks import recalculate_warehouse_shortages_task


class ProductionOrderStepViewSet(ModelViewSet):
    http_method_names = [
        "get",
        "post",
        "head",
        "options",
    ]
    permission_classes = [DjangoModelPermissions]
    queryset = ProductionOrderStep.objects.select_related(
        "production_order",
        "production_order__sales_order",
        "source_product_step",
    ).order_by(
        "production_order",
        "sequence_number",
        "id",
    )

    def get_serializer_class(self):
        from rest_framework import serializers

        class ProductionOrderStepSerializer(serializers.ModelSerializer):
            class Meta:
                model = ProductionOrderStep
                fields = [
                    "id",
                    "production_order",
                    "source_product_step",
                    "name",
                    "sequence_number",
                    "status",
                    "started_at",
                    "finished_at",
                    "created_at",
                ]
                read_only_fields = fields

        return ProductionOrderStepSerializer

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        with transaction.atomic():
            step = ProductionOrderStep.objects.select_for_update().get(pk=pk)

            self.check_object_permissions(request, step)

            if step.status != ProductionOrderStep.Status.DRAFT:
                raise ValidationError(
                    "Підтвердити можна лише етап у статусі draft."
                )

            previous_not_confirmed_steps = ProductionOrderStep.objects.filter(
                production_order=step.production_order,
                sequence_number__lt=step.sequence_number,
            ).exclude(
                status__in=[
                    ProductionOrderStep.Status.CONFIRMED,
                    ProductionOrderStep.Status.IN_PROGRESS,
                    ProductionOrderStep.Status.FINISHED,
                ],
            )

            if previous_not_confirmed_steps.exists():
                raise ValidationError(
                    "Неможливо підтвердити етап, доки попередні етапи не підтверджені."
                )

            result = reserve_components_for_production_step_confirmation(
                production_order_step=step,
                created_by=request.user,
            )

            step.status = ProductionOrderStep.Status.CONFIRMED
            step.save(update_fields=["status"])

            create_sales_order_event(
                sales_order=step.production_order.sales_order,
                event_type=SalesOrderEvent.EventType.PRODUCTION_ORDER_STEP_CONFIRMED,
                source=SalesOrderEvent.Source.PRODUCTION,
                title="Підтверджено етап виробництва",
                message=f"Підтверджено етап: {step.name}.",
                payload={
                    "production_order_id": step.production_order_id,
                    "production_order_step_id": step.id,
                    "sequence_number": step.sequence_number,
                    "reserved_components_count": len(result["components"]),
                },
                created_by=request.user,
            )

            inv_item_ids = result["inv_item_ids"]

            if inv_item_ids:
                transaction.on_commit(
                    lambda: recalculate_warehouse_shortages_task.delay(
                        inv_item_ids=inv_item_ids,
                    )
                )

        step = self.get_queryset().get(pk=step.pk)

        return Response({
            "production_order_step": step.id,
            "status": step.status,
            "reserved_components": result["components"],
        })