from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from production.models import (
    ProductionOrder,
    ProductionOrderStep,
)
from sales.models import SalesOrderEvent
from sales.services.events import create_sales_order_event
from warehouse.models import WarehouseProductionMovement


def start_production_order_step(
    *,
    production_order_step,
):
    if production_order_step.status != ProductionOrderStep.Status.CONFIRMED:
        raise ValidationError(
            "Запустити можна лише етап у статусі confirmed."
        )

    if (
        production_order_step.production_order.status
        != ProductionOrder.Status.IN_PROGRESS
    ):
        raise ValidationError(
            "ProductionOrder повинен бути у статусі in_progress."
        )

    if production_order_step.expected_finished_at is None:
        raise ValidationError(
            "Для етапу не заповнено expected_finished_at."
        )

    movement_exists = WarehouseProductionMovement.objects.filter(
        production_order_step=production_order_step,
        status=WarehouseProductionMovement.Status.EXECUTED,
    ).exists()

    if not movement_exists:
        raise ValidationError(
            "Неможливо запустити етап: компоненти ще не передані у виробництво."
        )

    previous_step = (
        ProductionOrderStep.objects.filter(
            production_order=production_order_step.production_order,
            sequence_number__lt=production_order_step.sequence_number,
        ).order_by(
            "-sequence_number",
            "-id",
        ).first()
    )

    if (
        previous_step is not None
        and previous_step.status != ProductionOrderStep.Status.FINISHED
    ):
        raise ValidationError(
            "Неможливо запустити етап, доки попередній етап не завершено."
        )

    now = timezone.now()

    with transaction.atomic():
        production_order_step.status = ProductionOrderStep.Status.IN_PROGRESS
        production_order_step.started_at = now

        production_order_step.save(
            update_fields=[
                "status",
                "started_at",
            ]
        )

        if previous_step is None:
            production_order = production_order_step.production_order

            if production_order.started_at is None:
                production_order.started_at = now
                production_order.save(
                    update_fields=[
                        "started_at",
                    ]
                )

        create_sales_order_event(
            sales_order=production_order_step.production_order.sales_order,
            event_type=SalesOrderEvent.EventType.PRODUCTION_ORDER_STEP_STARTED,
            source=SalesOrderEvent.Source.PRODUCTION,
            title="Запущено етап виробництва",
            message=f"Етап переведено у статус in_progress: {production_order_step.name}.",
            payload={
                "production_order_id": (
                    production_order_step.production_order_id
                ),
                "production_order_step_id": (
                    production_order_step.id
                ),
                "source_product_step_id": (
                    production_order_step.source_product_step_id
                ),
                "step_name": production_order_step.name,
                "sequence_number": (
                    production_order_step.sequence_number
                ),
                "expected_finished_at": (
                    production_order_step.expected_finished_at.isoformat()
                ),
            },
            created_by=None,
        )

    return production_order_step