from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from organizations.models import Organization

from warehouse.models import WarehouseUnit, WarehouseUnitEvent

from sales.tasks import (
    recalculate_customer_component_confirmation_issues_task,
)
from warehouse.services.intake_marking import (
    mark_tolling_receipt_document_sent_by_id_if_fully_processed,
    mark_tolling_receipt_document_sent_if_fully_processed,
)
from warehouse.tasks import (
    recalculate_warehouse_shortages_task,
)

def accept_tolling_receipt_item_to_location(
    *,
    receipt_item,
    location,
    created_by=None,
):
    receipt_document = receipt_item.receipt_document
    order_item = receipt_item.order_item

    if not receipt_document.completed:
        raise ValidationError("Документ приходу повинен бути завершеним.")

    if receipt_document.sent_to_warehouse:
        raise ValidationError("Документ приходу вже передано на склад.")

    if order_item.requires_unit_conversion:
        raise ValidationError(
            "Для цього рядка приходу потрібна окрема операція конвертації одиниць."
        )

    existing_units = WarehouseUnit.objects.filter(
        tolling_source_receipt_item=receipt_item,
    )
    if existing_units.exists():
        raise ValidationError("Цей рядок приходу вже оброблено складом.")

    whole_units = int(receipt_item.received_quantity)
    fractional_part = receipt_item.received_quantity - Decimal(whole_units)

    with transaction.atomic():
        units_to_create = []

        for _ in range(whole_units):
            units_to_create.append(
                WarehouseUnit(
                    inventory_item=order_item.inv_item,
                    location=location,
                    quantity=Decimal("1.000"),
                    tolling_source_receipt_item=receipt_item,
                    tolling_source_order_item=order_item,
                )
            )

        if fractional_part > 0:
            units_to_create.append(
                WarehouseUnit(
                    inventory_item=order_item.inv_item,
                    location=location,
                    quantity=fractional_part,
                    tolling_source_receipt_item=receipt_item,
                    tolling_source_order_item=order_item,
                )
            )

        for unit in units_to_create:
            unit.full_clean()

        created_units = WarehouseUnit.objects.bulk_create(units_to_create)

        events_to_create = [
            WarehouseUnitEvent(
                operation_type=WarehouseUnitEvent.OperationType.INTAKE,
                source_unit=None,
                result_unit=unit,
                quantity=unit.quantity,
                from_location=None,
                from_storage_place=None,
                to_location=unit.location,
                to_storage_place=unit.storage_place,
                created_by=created_by,
            )
            for unit in created_units
        ]

        for event in events_to_create:
            event.full_clean()

        WarehouseUnitEvent.objects.bulk_create(events_to_create)

        mark_tolling_receipt_document_sent_if_fully_processed(receipt_document)

    recalculate_customer_component_confirmation_issues_task.delay(
        organization_id=receipt_document.order.organization_id,
        inv_item_id=order_item.inv_item_id,
    )

    if receipt_document.order.organization.type == Organization.Type.CHARITY:
        recalculate_warehouse_shortages_task.delay(
            inv_item_ids=[order_item.inv_item_id],
        )

    return {
        "status": "ok",
        "created_units": len(units_to_create),
        "location_id": location.id,
        "receipt_item_id": receipt_item.id,
        "receipt_document_id": receipt_document.id,
        "sent_to_warehouse": receipt_document.sent_to_warehouse,
    }
    
def bulk_accept_tolling_receipt_items_to_location(
    *,
    receipt_item_ids,
    location,
    created_by=None,
):
    receipt_items = list(
        TollingReceiptItem.objects.select_related(
            "receipt_document",
            "order_item",
            "order_item__inv_item",
        ).filter(
            id__in=receipt_item_ids,
        )
    )

    found_ids = {item.id for item in receipt_items}
    missing_ids = [item_id for item_id in receipt_item_ids if item_id not in found_ids]
    if missing_ids:
        raise ValidationError({
            "receipt_item_ids": (
                f"Не знайдено рядки приходу з id: {missing_ids}"
            )
        })

    existing_units = set(
        WarehouseUnit.objects.filter(
            tolling_source_receipt_item_id__in=receipt_item_ids,
        ).values_list("tolling_source_receipt_item_id", flat=True)
    )
    if existing_units:
        raise ValidationError({
            "receipt_item_ids": (
                f"Деякі рядки приходу вже оброблено складом: {sorted(existing_units)}"
            )
        })

    units_to_create = []
    affected_receipt_document_ids = set()

    for receipt_item in receipt_items:
        receipt_document = receipt_item.receipt_document
        order_item = receipt_item.order_item

        if not receipt_document.completed:
            raise ValidationError(
                f"Документ приходу для рядка {receipt_item.id} повинен бути завершеним."
            )

        if receipt_document.sent_to_warehouse:
            raise ValidationError(
                f"Документ приходу для рядка {receipt_item.id} вже передано на склад."
            )

        if order_item.requires_unit_conversion:
            raise ValidationError(
                f"Рядок приходу {receipt_item.id} потребує окремої операції конвертації одиниць."
            )

        whole_units = int(receipt_item.received_quantity)
        fractional_part = receipt_item.received_quantity - Decimal(whole_units)
        affected_receipt_document_ids.add(receipt_document.id)

        for _ in range(whole_units):
            units_to_create.append(
                WarehouseUnit(
                    inventory_item=order_item.inv_item,
                    location=location,
                    quantity=Decimal("1.000"),
                    tolling_source_receipt_item=receipt_item,
                    tolling_source_order_item=order_item,
                )
            )

        if fractional_part > 0:
            units_to_create.append(
                WarehouseUnit(
                    inventory_item=order_item.inv_item,
                    location=location,
                    quantity=fractional_part,
                    tolling_source_receipt_item=receipt_item,
                    tolling_source_order_item=order_item,
                )
            )

    with transaction.atomic():
        for unit in units_to_create:
            unit.full_clean()

        created_units = WarehouseUnit.objects.bulk_create(units_to_create)

        events_to_create = [
            WarehouseUnitEvent(
                operation_type=WarehouseUnitEvent.OperationType.INTAKE,
                source_unit=None,
                result_unit=unit,
                quantity=unit.quantity,
                from_location=None,
                from_storage_place=None,
                to_location=unit.location,
                to_storage_place=unit.storage_place,
                created_by=created_by,
            )
            for unit in created_units
        ]

        for event in events_to_create:
            event.full_clean()

        WarehouseUnitEvent.objects.bulk_create(events_to_create)

        for receipt_document_id in affected_receipt_document_ids:
            mark_tolling_receipt_document_sent_by_id_if_fully_processed(
                receipt_document_id
            )

    affected_pairs = {
        (
            receipt_item.receipt_document.order.organization_id,
            receipt_item.order_item.inv_item_id,
        )
        for receipt_item in receipt_items
    }

    affected_shortage_item_ids = set()

    for receipt_item in receipt_items:
        if (
            receipt_item.receipt_document.order.organization.type
            == Organization.Type.CHARITY
        ):
            affected_shortage_item_ids.add(
                receipt_item.order_item.inv_item_id
            )

    for organization_id, inv_item_id in affected_pairs:
        recalculate_customer_component_confirmation_issues_task.delay(
            organization_id=organization_id,
            inv_item_id=inv_item_id,
        )

    if affected_shortage_item_ids:
        recalculate_warehouse_shortages_task.delay(
            inv_item_ids=list(affected_shortage_item_ids),
        )

    return {
        "status": "ok",
        "processed_receipt_item_ids": receipt_item_ids,
        "created_units": len(units_to_create),
        "location_id": location.id,
    }