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

    components_to_create = []

    for step_item in step_items:
        components_to_create.append(
            SalesOrderComponent(
                sales_order=sales_order,
                inv_item=step_item.inv_item,
                quantity=step_item.quantity,
                source_type=SalesOrderComponent.SourceType.STOCK,
                source_organization=None,
                is_required_for_start=step_item.inv_item.is_required_for_production_start,
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
    comment="",
):
    with transaction.atomic():
        sales_order = SalesOrder.objects.create(
            organization=organization,
            product=product,
            created_by=created_by,
            comment=comment,
        )

        create_sales_order_components(sales_order)

    return sales_order


def check_sales_order_can_confirm(sales_order):
    missing_components = []

    external_components = sales_order.components.select_related(
        "inv_item",
        "source_organization",
    ).filter(
        source_type__in=[
            SalesOrderComponent.SourceType.CUSTOMER,
            SalesOrderComponent.SourceType.DONATED,
        ],
        is_required_for_start=True,
    )

    for component in external_components:
        available_quantity = sum(
            (
                unit.quantity
                for unit in WarehouseUnit.objects.filter(
                    inventory_item=component.inv_item,
                    status=WarehouseUnit.Status.ON_STOCK,
                    tolling_source_order_item__order__organization=component.source_organization,
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
                "source_type": component.source_type,
                "source_organization": (
                    component.source_organization.id
                    if component.source_organization
                    else None
                ),
            })

    return {
        "can_confirm": len(missing_components) == 0,
        "missing_components": missing_components,
    }