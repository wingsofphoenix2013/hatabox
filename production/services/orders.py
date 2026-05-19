from django.db import transaction
from rest_framework.exceptions import ValidationError

from inventory.models import ProductStep
from production.models import (
    ProductionOrder,
    ProductionOrderStep,
    ProductionOrderStepComponent,
)
from warehouse.services.production_movement import (
    create_production_movements_for_order,
)
from sales.models import SalesOrder, SalesOrderComponent


def create_production_order_from_sales_order(
    *,
    sales_order,
):
    if sales_order.status != SalesOrder.Status.CONFIRMED:
        raise ValidationError(
            "ProductionOrder можна створити лише для підтвердженого SalesOrder."
        )

    with transaction.atomic():
        existing_production_order = ProductionOrder.objects.filter(
            sales_order=sales_order,
        ).first()

        if existing_production_order is not None:
            return existing_production_order

        production_order = ProductionOrder.objects.create(
            sales_order=sales_order,
        )

        sales_order_components_by_inv_item = {
            component.inv_item_id: component
            for component in sales_order.components.select_related("inv_item").all()
        }

        product_steps = list(
            ProductStep.objects.filter(
                product_id=sales_order.product_id,
            ).order_by(
                "sort_order",
                "id",
            )
        )

        sequence_number = 1

        for product_step in product_steps:
            production_order_step = ProductionOrderStep.objects.create(
                production_order=production_order,
                source_product_step=product_step,
                name=product_step.name,
                sequence_number=sequence_number,
            )

            sequence_number += 1

            step_items = product_step.step_items.select_related(
                "inv_item",
            ).order_by(
                "id",
            )

            step_components_to_create = []

            for step_item in step_items:
                sales_order_component = sales_order_components_by_inv_item.get(
                    step_item.inv_item_id,
                )

                if sales_order_component is None:
                    raise ValidationError(
                        "Не знайдено SalesOrderComponent для компонента ProductStepItem."
                    )

                step_components_to_create.append(
                    ProductionOrderStepComponent(
                        production_order_step=production_order_step,
                        source_product_step_item=step_item,
                        sales_order_component=sales_order_component,
                        inv_item=step_item.inv_item,
                        required_quantity=step_item.quantity,
                        is_required_for_step_start=step_item.inv_item.is_required_for_step_start,
                    )
                )

            ProductionOrderStepComponent.objects.bulk_create(
                step_components_to_create,
            )

    return production_order


def start_production_order(
    *,
    production_order,
    created_by=None,
):
    if production_order.status != ProductionOrder.Status.CONFIRMED:
        raise ValidationError(
            "Запуск виробництва можливий лише для confirmed ProductionOrder."
        )

    first_step = (
        production_order.steps.order_by(
            "sequence_number",
            "id",
        ).first()
    )

    if first_step is None:
        raise ValidationError(
            "ProductionOrder не містить жодного етапу."
        )

    if first_step.status != ProductionOrderStep.Status.CONFIRMED:
        raise ValidationError(
            "Перший етап виробництва повинен бути підтверджений."
        )

    with transaction.atomic():
        production_order.status = ProductionOrder.Status.IN_PROGRESS
        production_order.save(update_fields=["status"])

        sales_order = production_order.sales_order
        sales_order.status = SalesOrder.Status.IN_PROGRESS
        sales_order.save(update_fields=["status"])

        movement_result = create_production_movements_for_order(
            production_order=production_order,
            created_by=created_by,
        )

    return {
        "production_order_id": production_order.id,
        "sales_order_id": sales_order.id,
        "created_movements": movement_result["created_movements"],
    }