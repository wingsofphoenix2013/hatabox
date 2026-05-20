from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from production.models import ProductionOrderStep
from warehouse.models import WarehouseProductionMovement


def start_production_order_step(
    *,
    production_order_step,
):
    if production_order_step.status != ProductionOrderStep.Status.CONFIRMED:
        raise ValidationError(
            "Запустити можна лише етап у статусі confirmed."
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

    return production_order_step