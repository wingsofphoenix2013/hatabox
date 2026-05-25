from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from inventory.models import ProductStepItem
from sales.models import (
    SalesOrder,
    SalesOrderComponent,
    SalesOrderEvent,
    SalesOrderIssue,
)
from sales.services.events import create_sales_order_event
from sales.services.issues import (
    recalculate_customer_component_confirmation_issues,
)


def change_sales_order_product(
    *,
    sales_order,
    new_product,
    created_by=None,
):
    if sales_order.status != SalesOrder.Status.DRAFT:
        raise ValidationError(
            "Змінювати версію виробу можна лише для draft SalesOrder."
        )

    old_product = sales_order.product

    if old_product.id == new_product.id:
        return {
            "added_components": [],
            "removed_components": [],
            "updated_components": [],
        }

    if (
        old_product.product_family_id
        != new_product.product_family_id
    ):
        raise ValidationError(
            "Можна змінювати лише версію виробу в межах однієї product family."
        )

    if hasattr(sales_order, "production_order"):
        raise ValidationError(
            "Для SalesOrder вже створено ProductionOrder."
        )

    old_components = list(
        sales_order.components.select_related(
            "inv_item",
        )
    )

    old_components_by_item_id = {
        component.inv_item_id: component
        for component in old_components
    }

    new_step_items = ProductStepItem.objects.select_related(
        "inv_item",
    ).filter(
        product_step__product=new_product,
    )

    new_components_by_item_id = {}

    for step_item in new_step_items:
        inv_item_id = step_item.inv_item_id

        if inv_item_id not in new_components_by_item_id:
            new_components_by_item_id[inv_item_id] = {
                "inv_item": step_item.inv_item,
                "quantity": Decimal("0.000"),
            }

        new_components_by_item_id[inv_item_id]["quantity"] += (
            step_item.quantity
        )

    added_components = []
    removed_components = []
    updated_components = []

    affected_customer_item_ids = set()

    with transaction.atomic():
        sales_order.product = new_product
        sales_order.save(
            update_fields=[
                "product",
                "updated_at",
            ]
        )

        for inv_item_id, component_data in new_components_by_item_id.items():
            old_component = old_components_by_item_id.get(
                inv_item_id,
            )

            if old_component is None:
                SalesOrderComponent.objects.create(
                    sales_order=sales_order,
                    inv_item=component_data["inv_item"],
                    quantity=component_data["quantity"],
                    fulfillment_mode=SalesOrderComponent.FulfillmentMode.MIXED,
                )

                added_components.append({
                    "inv_item_id": inv_item_id,
                    "quantity": str(component_data["quantity"]),
                })

                continue

            old_quantity = old_component.quantity
            new_quantity = component_data["quantity"]

            if old_quantity != new_quantity:
                updated_components.append({
                    "inv_item_id": inv_item_id,
                    "old_quantity": str(old_quantity),
                    "new_quantity": str(new_quantity),
                })

            old_component.quantity = new_quantity
            old_component.save(
                update_fields=[
                    "quantity",
                ]
            )

            if (
                old_component.fulfillment_mode
                == SalesOrderComponent.FulfillmentMode.CUSTOMER
            ):
                affected_customer_item_ids.add(inv_item_id)

        new_item_ids = set(
            new_components_by_item_id.keys()
        )

        for old_component in old_components:
            if old_component.inv_item_id in new_item_ids:
                continue

            removed_components.append({
                "inv_item_id": old_component.inv_item_id,
                "quantity": str(old_component.quantity),
            })

            if (
                old_component.fulfillment_mode
                == SalesOrderComponent.FulfillmentMode.CUSTOMER
            ):
                affected_customer_item_ids.add(
                    old_component.inv_item_id
                )

                SalesOrderIssue.objects.filter(
                    sales_order=sales_order,
                    stage=SalesOrderIssue.Stage.CONFIRMATION,
                    issue_type=(
                        SalesOrderIssue.IssueType.CUSTOMER_COMPONENT_MISSING
                    ),
                    related_component=old_component,
                    status=SalesOrderIssue.Status.OPEN,
                ).update(
                    status=SalesOrderIssue.Status.RESOLVED,
                    resolved_at=timezone.now(),
                    last_checked_at=timezone.now(),
                )

            old_component.delete()

        for inv_item_id in affected_customer_item_ids:
            recalculate_customer_component_confirmation_issues(
                organization_id=sales_order.organization_id,
                inv_item_id=inv_item_id,
            )

        create_sales_order_event(
            sales_order=sales_order,
            event_type=SalesOrderEvent.EventType.SALES_ORDER_PRODUCT_CHANGED,
            source=SalesOrderEvent.Source.SALES,
            title="Змінено версію виробу",
            message=(
                f"Версію виробу змінено з "
                f"{old_product.code} "
                f"на {new_product.code}."
            ),
            payload={
                "old_product_id": old_product.id,
                "old_product_code": old_product.code,

                "new_product_id": new_product.id,
                "new_product_code": new_product.code,

                "added_components": added_components,
                "removed_components": removed_components,
                "updated_components": updated_components,
            },
            created_by=created_by,
        )

    return {
        "added_components": added_components,
        "removed_components": removed_components,
        "updated_components": updated_components,
    }