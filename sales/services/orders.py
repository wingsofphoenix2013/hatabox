from decimal import Decimal

from django.db import transaction

from warehouse.services.sales_order_availability import build_sales_order_availability
from inventory.models import ProductStepItem
from sales.models import SalesOrder, SalesOrderComponent


def create_sales_order_components(sales_order):
    if sales_order.components.exists():
        return

    step_items = ProductStepItem.objects.select_related(
        "inv_item",
    ).filter(
        product_step__product_id=sales_order.product_id,
    )

    components_by_inv_item = {}

    for step_item in step_items:
        inv_item_id = step_item.inv_item_id

        if inv_item_id not in components_by_inv_item:
            components_by_inv_item[inv_item_id] = {
                "inv_item": step_item.inv_item,
                "quantity": Decimal("0.000"),
            }

        components_by_inv_item[inv_item_id]["quantity"] += step_item.quantity

    components_to_create = []

    for component_data in components_by_inv_item.values():
        components_to_create.append(
            SalesOrderComponent(
                sales_order=sales_order,
                inv_item=component_data["inv_item"],
                quantity=component_data["quantity"],
                fulfillment_mode=SalesOrderComponent.FulfillmentMode.MIXED,
                is_required_for_start=component_data["inv_item"].is_required_for_production_start,
            )
        )

    for component in components_to_create:
        component.full_clean()

    SalesOrderComponent.objects.bulk_create(components_to_create)


def create_sales_order(
    *,
    organization,
    product,
    created_by,
    customer_responsible_person=None,
    comment="",
):
    with transaction.atomic():
        sales_order = SalesOrder.objects.create(
            organization=organization,
            product=product,
            created_by=created_by,
            customer_responsible_person=customer_responsible_person,
            comment=comment,
        )

        create_sales_order_components(sales_order)

    return sales_order


def check_sales_order_can_confirm(sales_order):
    availability = build_sales_order_availability(
        sales_order_id=sales_order.id,
    )

    missing_components = [
        component
        for component in availability["components"]
        if (
            component["fulfillment_mode"] == SalesOrderComponent.FulfillmentMode.CUSTOMER
            and component["is_required_for_start"]
            and not component["can_cover"]
        )
    ]

    return {
        "can_confirm": availability["can_confirm"],
        "missing_components": missing_components,
    }