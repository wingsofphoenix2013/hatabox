from django.db import transaction

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
            )
        )

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