from decimal import Decimal

from django.db import models, transaction
from rest_framework.exceptions import ValidationError

from orders.models import (
    ExternalOrder,
    ExternalOrderItem,
    ReclamationReturnDocument,
    ReclamationReturnItem,
)
from warehouse.models import (
    WarehouseUnit,
    WarehouseUnitEvent,
)
from warehouse.tasks import recalculate_warehouse_shortages_task


def create_reclamation_return_draft_from_cart(
    *,
    order,
    reason,
    return_date,
    items,
    comment="",
    created_by=None,
):
    if not items:
        raise ValidationError({
            "items": "Потрібно додати хоча б одну позицію для повернення."
        })

    with transaction.atomic():
        reclamation_document = ReclamationReturnDocument.objects.create(
            return_no=f"REC-{order.order_no}-{ReclamationReturnDocument.objects.filter(order=order).count() + 1}",
            order=order,
            status=ReclamationReturnDocument.StatusChoices.DRAFT,
            return_date=return_date,
            reason=reason,
            comment=comment,
            created_by=created_by,
        )

        if not order.has_reclamation:
            order.has_reclamation = True
            order.save(update_fields=["has_reclamation"])

        affected_inv_item_ids = set()

        for row in items:
            order_item_id = row["order_item"]
            quantity = Decimal(str(row["quantity"]))

            if quantity <= 0:
                raise ValidationError({
                    "items": "Кількість повернення повинна бути більше 0."
                })

            try:
                order_item = ExternalOrderItem.objects.select_related(
                    "vendor_item",
                    "vendor_item__item",
                ).get(
                    id=order_item_id,
                    order=order,
                )
            except ExternalOrderItem.DoesNotExist:
                raise ValidationError({
                    "items": "Позиція повернення не належить цьому замовленню."
                })

            available_unit_ids = list(
                WarehouseUnit.objects.select_for_update().filter(
                    source_order_item=order_item,
                    status=WarehouseUnit.Status.ON_STOCK,
                ).order_by("id").values_list("id", flat=True)
            )

            available_units = list(
                WarehouseUnit.objects.select_related(
                    "location",
                    "storage_place",
                    "storage_place__location",
                ).filter(
                    id__in=available_unit_ids,
                ).order_by("id")
            )

            selected_units = []
            selected_quantity = Decimal("0.000")

            for unit in available_units:
                selected_units.append(unit)
                selected_quantity += unit.quantity

                if selected_quantity >= quantity:
                    break

            if selected_quantity != quantity:
                raise ValidationError({
                    "items": (
                        f"Недостатньо доступної кількості для повернення "
                        f"по позиції {order_item.id}."
                    )
                })

            affected_inv_item_ids.add(order_item.vendor_item.item_id)

            selected_unit_ids = [
                unit.id
                for unit in selected_units
            ]

            split_events = WarehouseUnitEvent.objects.filter(
                operation_type=WarehouseUnitEvent.OperationType.SPLIT_MOVE,
            ).filter(
                models.Q(source_unit_id__in=selected_unit_ids)
                | models.Q(result_unit_id__in=selected_unit_ids)
            )

            if split_events.exists():
                raise ValidationError({
                    "items": (
                        f"Деякі складські одиниці по позиції {order_item.id} "
                        f"брали участь у split і не можуть бути повернені."
                    )
                })

            return_items_to_create = []

            for unit in selected_units:
                source_location = unit.location
                source_storage_place = unit.storage_place

                if source_storage_place is not None:
                    source_location = source_storage_place.location

                return_items_to_create.append(
                    ReclamationReturnItem(
                        return_document=reclamation_document,
                        order_item=order_item,
                        warehouse_unit=unit,
                        quantity=unit.quantity,
                        source_location=source_location,
                        source_storage_place=source_storage_place,
                        source_location_code=source_location.code if source_location else "",
                        source_location_name=source_location.name if source_location else "",
                        source_storage_place_code=source_storage_place.code if source_storage_place else "",
                        source_storage_place_display_name=(
                            source_storage_place.get_display_name()
                            if source_storage_place
                            else ""
                        ),
                        source_storage_place_full_display=(
                            source_storage_place.get_display_name_verbose()
                            if source_storage_place
                            else ""
                        ),
                    )
                )

                unit.status = WarehouseUnit.Status.BLOCKED

            WarehouseUnit.objects.bulk_update(
                selected_units,
                ["status", "updated_at"],
            )

            ReclamationReturnItem.objects.bulk_create(
                return_items_to_create,
            )

        if affected_inv_item_ids:
            recalculate_warehouse_shortages_task.delay(
                inv_item_ids=list(affected_inv_item_ids),
            )

        return reclamation_document
        
def get_reclamation_return_availability(
    *,
    order,
):
    results = []

    order_items = ExternalOrderItem.objects.select_related(
        "vendor_item",
        "vendor_item__item",
    ).filter(
        order=order,
    ).order_by("id")

    for order_item in order_items:
        units = WarehouseUnit.objects.filter(
            source_order_item=order_item,
        )

        available_quantity = Decimal("0.000")
        blocked_quantity = Decimal("0.000")
        returned_quantity = Decimal("0.000")
        received_quantity = Decimal("0.000")

        for unit in units:
            received_quantity += unit.quantity

            if unit.status == WarehouseUnit.Status.ON_STOCK:
                available_quantity += unit.quantity

            elif unit.status == WarehouseUnit.Status.BLOCKED:
                blocked_quantity += unit.quantity

            elif unit.status == WarehouseUnit.Status.RETURNED:
                returned_quantity += unit.quantity

        results.append({
            "order_item_id": order_item.id,
            "vendor_item_id": order_item.vendor_item_id,
            "vendor_item_name": order_item.vendor_item.name,
            "inventory_item_id": order_item.vendor_item.item_id,
            "inventory_item_code": order_item.vendor_item.item.internal_code,
            "inventory_item_name": order_item.vendor_item.item.name,
            "ordered_quantity": order_item.quantity,
            "received_quantity": received_quantity,
            "available_quantity": available_quantity,
            "blocked_quantity": blocked_quantity,
            "returned_quantity": returned_quantity,
        })

    return results