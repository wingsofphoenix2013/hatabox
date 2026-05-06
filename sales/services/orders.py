from django.db import transaction

from decimal import Decimal

from warehouse.models import WarehouseUnit
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
    missing_components = []

    external_components = sales_order.components.select_related(
        "inv_item",
    ).filter(
        fulfillment_mode=SalesOrderComponent.FulfillmentMode.CUSTOMER,
        is_required_for_start=True,
    )

    for component in external_components:
        available_quantity = sum(
            (
                unit.quantity
                for unit in WarehouseUnit.objects.filter(
                    inventory_item=component.inv_item,
                    status=WarehouseUnit.Status.ON_STOCK,
                    tolling_source_order_item__order__organization=sales_order.organization,
                )
            ),
            Decimal("0.000"),
        )

        if available_quantity < component.quantity:
            missing_components.append({
                "component_id": component.id,
                "inv_item": component.inv_item.id,
                "inv_item_code": component.inv_item.internal_code,
                "inv_item_name": component.inv_item.name,
                "required_quantity": component.quantity,
                "available_quantity": available_quantity,
                "fulfillment_mode": component.fulfillment_mode,
            })

    return {
        "can_confirm": len(missing_components) == 0,
        "missing_components": missing_components,
    }