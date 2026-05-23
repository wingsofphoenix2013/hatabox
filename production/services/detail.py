from django.utils import timezone

from production.models import (
    ProductionOrder,
    ProductionOrderStep,
)
from warehouse.models import (
    WarehouseProductionMovement,
)


def build_production_order_detail(
    *,
    production_order,
):
    steps = list(
        production_order.steps.order_by(
            "sequence_number",
            "id",
        )
    )

    movement_by_step_id = {
        movement.production_order_step_id: movement
        for movement in WarehouseProductionMovement.objects.filter(
            production_order=production_order,
        ).order_by(
            "-created_at",
            "-id",
        )
    }

    current_step = None

    if production_order.status != ProductionOrder.Status.READY:
        current_step = next(
            (
                step
                for step in steps
                if step.status == ProductionOrderStep.Status.IN_PROGRESS
            ),
            None,
        )

        if current_step is None:
            current_step = next(
                (
                    step
                    for step in steps
                    if step.status == ProductionOrderStep.Status.CONFIRMED
                ),
                None,
            )

    current_step_movement = (
        movement_by_step_id.get(current_step.id)
        if current_step
        else None
    )

    summary = {
        "sales_order": production_order.sales_order_id,
        "sales_order_created_at": (
            production_order.sales_order.created_at
        ),

        "production_order": production_order.id,
        "production_order_status": production_order.status,
        "production_order_status_display": (
            production_order.get_status_display()
        ),

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

        "comment": production_order.comment,

        "started_at": production_order.started_at,
        "expected_ready_at": production_order.expected_ready_at,
        "ready_at": production_order.ready_at,

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
        "current_step_status_display": (
            current_step.get_status_display()
            if current_step
            else None
        ),

        "current_step_components_transferred": (
            current_step_movement is not None
            and current_step_movement.status
            == WarehouseProductionMovement.Status.EXECUTED
        ),
    }

    steps_payload = []

    for step in steps:
        movement = movement_by_step_id.get(step.id)

        current_is_overdue = False
        current_days_left = None

        final_is_overdue = False
        final_overdue_days = None

        if step.expected_finished_at is not None:
            if step.finished_at is None:
                current_days_left = (
                    step.expected_finished_at.date()
                    - timezone.now().date()
                ).days

                current_is_overdue = (
                    current_days_left < 0
                )

            else:
                final_overdue_days = (
                    step.finished_at.date()
                    - step.expected_finished_at.date()
                ).days

                final_is_overdue = (
                    final_overdue_days > 0
                )

        steps_payload.append({
            "production_order_step": step.id,
            "source_product_step": step.source_product_step_id,

            "name": step.name,

            "status": step.status,
            "status_display": step.get_status_display(),

            "started_at": step.started_at,
            "expected_finished_at": step.expected_finished_at,
            "finished_at": step.finished_at,

            "current_is_overdue": current_is_overdue,
            "current_days_left": current_days_left,

            "final_is_overdue": final_is_overdue,
            "final_overdue_days": final_overdue_days,

            "production_movement": (
                movement.id
                if movement
                else None
            ),
            "production_movement_status": (
                movement.status
                if movement
                else None
            ),

            "components_transferred": (
                movement is not None
                and movement.status
                == WarehouseProductionMovement.Status.EXECUTED
            ),

            "production_movement_invoice_file": (
                movement.invoice_file.url
                if movement and movement.invoice_file
                else None
            ),
        })

    return {
        "summary": summary,
        "steps": steps_payload,
    }