from django.db import transaction
from rest_framework.exceptions import ValidationError

from production.models import (
    ProductionOrder,
    ProductionOrderStep,
)
from sales.models import SalesOrderEvent
from sales.services.events import create_sales_order_event


def update_production_order_steps_schedule(
    *,
    production_order,
    steps_data,
    created_by=None,
):
    if production_order.status != ProductionOrder.Status.IN_PROGRESS:
        raise ValidationError(
            "Графік можна редагувати лише для ProductionOrder у статусі in_progress."
        )

    production_steps = list(
        production_order.steps.order_by(
            "sequence_number",
            "id",
        )
    )

    step_by_id = {
        step.id: step
        for step in production_steps
    }

    updated_dates = {}

    for row in steps_data:
        step_id = row["production_order_step"]

        if step_id not in step_by_id:
            raise ValidationError({
                "production_order_step": (
                    "Етап не належить до цього ProductionOrder."
                )
            })

        step = step_by_id[step_id]

        if step.status != ProductionOrderStep.Status.CONFIRMED:
            raise ValidationError({
                "production_order_step": (
                    "Редагувати графік можна лише для confirmed етапів."
                )
            })

        updated_dates[step.id] = row["expected_finished_at"]

    effective_dates = {
        step.id: step.expected_finished_at
        for step in production_steps
    }

    effective_dates.update(updated_dates)

    changed_steps = []

    for index, step in enumerate(production_steps):
        current_date = effective_dates[step.id]

        if current_date is None:
            continue

        previous_step = (
            production_steps[index - 1]
            if index > 0
            else None
        )

        if previous_step is not None:
            previous_date = effective_dates[previous_step.id]

            if previous_date is None:
                raise ValidationError({
                    "expected_finished_at": (
                        "У попереднього етапу відсутня дата завершення."
                    )
                })

            if current_date <= previous_date:
                raise ValidationError({
                    "expected_finished_at": (
                        "Дата етапу повинна бути пізніше попереднього етапу."
                    )
                })

        if step.expected_finished_at != current_date:
            changed_steps.append({
                "production_order_step": step.id,
                "source_product_step": step.source_product_step_id,
                "old_expected_finished_at": (
                    step.expected_finished_at.isoformat()
                    if step.expected_finished_at
                    else None
                ),
                "new_expected_finished_at": (
                    current_date.isoformat()
                    if current_date
                    else None
                ),
            })

    if not changed_steps:
        return {
            "updated_steps": [],
        }

    with transaction.atomic():
        for step in production_steps:
            new_date = effective_dates[step.id]

            if step.expected_finished_at == new_date:
                continue

            step.expected_finished_at = new_date

        ProductionOrderStep.objects.bulk_update(
            production_steps,
            ["expected_finished_at"],
        )

        create_sales_order_event(
            sales_order=production_order.sales_order,
            event_type=SalesOrderEvent.EventType.PRODUCTION_STEP_SCHEDULE_UPDATED,
            source=SalesOrderEvent.Source.PRODUCTION,
            title="Оновлено графік виробництва",
            message="Оновлено планові дати виробничих етапів.",
            payload={
                "production_order_id": production_order.id,
                "updated_steps": changed_steps,
            },
            created_by=created_by,
        )

    return {
        "updated_steps": changed_steps,
    }