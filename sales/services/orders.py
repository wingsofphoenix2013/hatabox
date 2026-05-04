from django.db import transaction

from sales.models import SalesOrder, SalesOrderComponent


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

        components_to_create = []

        for step in product.steps.prefetch_related("step_items__inv_item").all():
            for step_item in step.step_items.all():
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

    return sales_order