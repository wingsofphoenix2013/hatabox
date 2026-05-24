from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from production.models import (
    ProductionOrder,
    ProductionOrderStep,
)
from sales.models import (
    SalesOrder,
    SalesOrderEvent,
)
from sales.services.events import create_sales_order_event
from warehouse.models import (
    WarehouseProductionMovement,
    WarehouseProductionMovementItem,
    WarehouseUnit,
    WarehouseUnitEvent,
)


def finish_production_order_step(
    *,
    production_order_step,
    created_by=None,
):
    step = production_order_step
    production_order = step.production_order

    if production_order.status != ProductionOrder.Status.IN_PROGRESS:
        raise ValidationError(
            "ProductionOrder повинен бути у статусі in_progress."
        )

    if step.status != ProductionOrderStep.Status.IN_PROGRESS:
        raise ValidationError(
            "Завершити можна лише етап у статусі in_progress."
        )

    if (
        production_order.use_work_tracking
        or production_order.use_hr_tracking
    ):
        raise ValidationError(
            "Для цього ProductionOrder увімкнений tracking робіт або персоналу."
        )

    movement_items = list(
        WarehouseProductionMovementItem.objects.select_related(
            "movement",
            "result_warehouse_unit",
        ).filter(
            movement__production_order_step=step,
            movement__status=WarehouseProductionMovement.Status.EXECUTED,
        )
    )

    now = timezone.now()

    with transaction.atomic():
        step.status = ProductionOrderStep.Status.FINISHED
        step.finished_at = now

        step.save(
            update_fields=[
                "status",
                "finished_at",
            ]
        )

        consumed_units = []
        warehouse_events = []

        for item in movement_items:
            result_unit = item.result_warehouse_unit

            if result_unit is None:
                continue

            result_unit.status = WarehouseUnit.Status.CONSUMED
            consumed_units.append(result_unit)

            warehouse_events.append(
                WarehouseUnitEvent(
                    operation_type=WarehouseUnitEvent.OperationType.PRODUCTION_CONSUME,
                    source_unit=result_unit,
                    result_unit=result_unit,
                    quantity=result_unit.quantity,
                    from_location=None,
                    from_storage_place=None,
                    to_location=None,
                    to_storage_place=None,
                    created_by=created_by,
                )
            )

        if consumed_units:
            WarehouseUnit.objects.bulk_update(
                consumed_units,
                [
                    "status",
                    "updated_at",
                ],
            )

        if warehouse_events:
            WarehouseUnitEvent.objects.bulk_create(
                warehouse_events,
            )

        create_sales_order_event(
            sales_order=production_order.sales_order,
            event_type=SalesOrderEvent.EventType.PRODUCTION_ORDER_STEP_FINISHED,
            source=SalesOrderEvent.Source.PRODUCTION,
            title="Завершено етап виробництва",
            message=f"Етап завершено: {step.name}.",
            payload={
                "production_order_id": production_order.id,
                "production_order_step_id": step.id,
                "source_product_step_id": (
                    step.source_product_step_id
                ),
                "step_name": step.name,
                "sequence_number": (
                    step.sequence_number
                ),
                "started_at": (
                    step.started_at.isoformat()
                    if step.started_at
                    else None
                ),
                "expected_finished_at": (
                    step.expected_finished_at.isoformat()
                    if step.expected_finished_at
                    else None
                ),
                "finished_at": now.isoformat(),
                "consumed_units": [
                    unit.id
                    for unit in consumed_units
                ],
            },
            created_by=created_by,
        )

        all_steps_finished = not ProductionOrderStep.objects.filter(
            production_order=production_order,
        ).exclude(
            status=ProductionOrderStep.Status.FINISHED,
        ).exists()

        if all_steps_finished:
            production_order.status = ProductionOrder.Status.READY
            production_order.ready_at = now

            production_order.save(
                update_fields=[
                    "status",
                    "ready_at",
                ]
            )

            sales_order = production_order.sales_order

            sales_order.status = SalesOrder.Status.READY

            sales_order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            create_sales_order_event(
                sales_order=sales_order,
                event_type=SalesOrderEvent.EventType.PRODUCTION_ORDER_READY,
                source=SalesOrderEvent.Source.PRODUCTION,
                title="Виробництво завершено",
                message="ProductionOrder переведено у статус ready.",
                payload={
                    "production_order_id": production_order.id,
                    "ready_at": now.isoformat(),
                },
                created_by=created_by,
            )

    return {
        "production_order_step": step.id,
        "status": step.status,
        "finished_at": step.finished_at,
    }