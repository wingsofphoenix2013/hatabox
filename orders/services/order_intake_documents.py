from django.db import transaction

from orders.models import (
    OrderIntakeDocument,
    OrderIntakeDocumentItem,
)


@transaction.atomic
def create_order_intake_document_from_external_receipt(
    receipt_document,
):
    intake_document, created = OrderIntakeDocument.objects.get_or_create(
        external_receipt_document=receipt_document,
        defaults={
            "source_flow": OrderIntakeDocument.SourceFlow.PROCUREMENT,
        },
    )

    if not created:
        return intake_document

    items_to_create = []

    for receipt_item in receipt_document.items.select_related(
        "order_item",
        "order_item__vendor_item",
        "order_item__vendor_item__item",
    ):
        order_item = receipt_item.order_item

        items_to_create.append(
            OrderIntakeDocumentItem(
                intake_document=intake_document,
                external_receipt_item=receipt_item,
                inventory_item=order_item.vendor_item.item,
                source_quantity=receipt_item.received_quantity,
                requires_unit_conversion=order_item.requires_unit_conversion,
            )
        )

    if items_to_create:
        OrderIntakeDocumentItem.objects.bulk_create(
            items_to_create,
        )

    return intake_document


@transaction.atomic
def create_order_intake_document_from_tolling_receipt(
    receipt_document,
):
    intake_document, created = OrderIntakeDocument.objects.get_or_create(
        tolling_receipt_document=receipt_document,
        defaults={
            "source_flow": OrderIntakeDocument.SourceFlow.TOLLING,
        },
    )

    if not created:
        return intake_document

    items_to_create = []

    for receipt_item in receipt_document.items.select_related(
        "order_item",
        "order_item__inv_item",
    ):
        order_item = receipt_item.order_item

        items_to_create.append(
            OrderIntakeDocumentItem(
                intake_document=intake_document,
                tolling_receipt_item=receipt_item,
                inventory_item=order_item.inv_item,
                source_quantity=receipt_item.received_quantity,
                requires_unit_conversion=False,
            )
        )

    if items_to_create:
        OrderIntakeDocumentItem.objects.bulk_create(
            items_to_create,
        )

    return intake_document