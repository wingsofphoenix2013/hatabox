from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from sales.models import SalesOrderEvent
from sales.services.events import create_sales_order_event
from warehouse.models import (
    WarehouseProductionMovement,
)


def request_production_movement_issue(
    *,
    movement,
    requested_by,
):
    if movement.status != WarehouseProductionMovement.Status.CREATED:
        raise ValidationError(
            "Запросити видачу можна лише для created накладної."
        )

    if not movement.invoice_file:
        raise ValidationError(
            "Для накладної ще не сформовано PDF."
        )

    if movement.issue_requested:
        return movement

    now = timezone.now()

    with transaction.atomic():
        movement.issue_requested = True
        movement.issue_requested_at = now
        movement.issue_requested_by = requested_by

        movement.save(
            update_fields=[
                "issue_requested",
                "issue_requested_at",
                "issue_requested_by",
            ]
        )

        create_sales_order_event(
            sales_order=movement.production_order.sales_order,
            event_type=(
                SalesOrderEvent.EventType.PRODUCTION_MOVEMENT_ISSUE_REQUESTED
            ),
            source=SalesOrderEvent.Source.PRODUCTION,
            title="Запрошено видачу комплекту у виробництво",
            message=(
                f"Запрошено видачу комплекту "
                f"для етапу "
                f"{movement.production_order_step.sequence_number}: "
                f"{movement.production_order_step.name}."
            ),
            payload={
                "production_movement_id": movement.id,
                "production_order_id": (
                    movement.production_order_id
                ),
                "production_order_step_id": (
                    movement.production_order_step_id
                ),
                "source_product_step_id": (
                    movement.production_order_step.source_product_step_id
                ),
                "source_product_step_name": (
                    movement.production_order_step.name
                ),
                "requested_by": (
                    requested_by.id
                    if requested_by
                    else None
                ),
                "requested_at": now.isoformat(),
            },
            created_by=requested_by,
        )

    return movement