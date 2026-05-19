from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from production.models import ProductionOrderStep
from sales.models import SalesOrderEvent
from sales.services.events import create_sales_order_event
from warehouse.models import (
    WarehouseProductionMovement,
    WarehouseProductionMovementItem,
    WarehouseProductionReservation,
    WarehouseUnit,
    WarehouseUnitEvent,
)


def create_production_movements_for_order(
    *,
    production_order,
    created_by=None,
):
    confirmed_steps = list(
        ProductionOrderStep.objects.filter(
            production_order=production_order,
            status=ProductionOrderStep.Status.CONFIRMED,
        ).order_by(
            "sequence_number",
            "id",
        )
    )

    created_movements = []

    with transaction.atomic():
        for step in confirmed_steps:
            existing_created_movement = (
                WarehouseProductionMovement.objects.filter(
                    production_order_step=step,
                    status=WarehouseProductionMovement.Status.CREATED,
                ).exists()
            )

            if existing_created_movement:
                continue

            reservations = list(
                WarehouseProductionReservation.objects.select_related(
                    "warehouse_unit",
                    "warehouse_unit__location",
                    "warehouse_unit__storage_place",
                    "warehouse_unit__storage_place__location",
                    "production_order_step_component",
                    "production_order_step_component__production_order_step",
                ).filter(
                    production_order_step_component__production_order_step=step,
                    status=WarehouseProductionReservation.Status.ACTIVE,
                ).order_by(
                    "warehouse_unit__inventory_item_id",
                    "id",
                )
            )

            if not reservations:
                raise ValidationError(
                    f"Для етапу '{step.name}' немає активних резервувань."
                )

            movement = WarehouseProductionMovement.objects.create(
                production_order=production_order,
                production_order_step=step,
                status=WarehouseProductionMovement.Status.CREATED,
                created_by=created_by,
            )

            items_to_create = []

            for reservation in reservations:
                unit = reservation.warehouse_unit

                if unit.storage_place is not None:
                    source_location = unit.storage_place.location
                    source_storage_place = unit.storage_place

                    source_storage_place_code = (
                        source_storage_place.code
                    )
                    source_storage_place_display_name = (
                        source_storage_place.get_display_name()
                    )
                    source_storage_place_full_display = (
                        source_storage_place.get_display_name_verbose()
                    )
                else:
                    source_location = unit.location
                    source_storage_place = None

                    source_storage_place_code = ""
                    source_storage_place_display_name = ""
                    source_storage_place_full_display = ""

                items_to_create.append(
                    WarehouseProductionMovementItem(
                        movement=movement,
                        production_reservation=reservation,
                        source_warehouse_unit=unit,
                        inventory_item_id=unit.inventory_item_id,
                        quantity=reservation.quantity,
                        executed_source_location=source_location,
                        executed_source_location_code=(
                            source_location.code
                        ),
                        executed_source_location_name=(
                            source_location.name
                        ),
                        executed_source_storage_place=(
                            source_storage_place
                        ),
                        executed_source_storage_place_code=(
                            source_storage_place_code
                        ),
                        executed_source_storage_place_display_name=(
                            source_storage_place_display_name
                        ),
                        executed_source_storage_place_full_display=(
                            source_storage_place_full_display
                        ),
                    )
                )

            WarehouseProductionMovementItem.objects.bulk_create(
                items_to_create,
            )

            created_movements.append(movement)

    return {
        "production_order_id": production_order.id,
        "created_movements": [
            {
                "movement_id": movement.id,
                "production_order_step_id": (
                    movement.production_order_step_id
                ),
            }
            for movement in created_movements
        ],
    }


ZERO = Decimal("0.000")


def _to_decimal(value) -> Decimal:
    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def cancel_production_movement(
    *,
    movement,
):
    if movement.status != WarehouseProductionMovement.Status.CREATED:
        raise ValidationError(
            "Можна скасувати лише created документ."
        )

    with transaction.atomic():
        movement.status = WarehouseProductionMovement.Status.CANCELLED
        movement.cancelled_at = timezone.now()

        movement.save(
            update_fields=[
                "status",
                "cancelled_at",
            ]
        )

    return movement


def execute_production_movement(
    *,
    movement,
    created_by=None,
):
    if movement.status != WarehouseProductionMovement.Status.CREATED:
        raise ValidationError(
            "Виконати можна лише created документ."
        )

    if not movement.invoice_file:
        raise ValidationError(
            "Неможливо виконати документ без сформованої накладної."
        )

    items = list(
        movement.items.select_related(
            "production_reservation",
            "source_warehouse_unit",
            "source_warehouse_unit__inventory_item",
            "source_warehouse_unit__location",
            "source_warehouse_unit__storage_place",
            "inventory_item",
        ).order_by(
            "inventory_item_id",
            "id",
        )
    )

    if not items:
        raise ValidationError(
            "Документ не містить жодної позиції."
        )

    items_by_inventory_item = defaultdict(list)

    for item in items:
        reservation = item.production_reservation
        source_unit = item.source_warehouse_unit

        if reservation.status != WarehouseProductionReservation.Status.ACTIVE:
            raise ValidationError(
                "У документі є резервування, яке вже не є active."
            )

        if source_unit.status != WarehouseUnit.Status.BLOCKED:
            raise ValidationError(
                "У документі є складська одиниця, яка вже не заблокована."
            )

        items_by_inventory_item[item.inventory_item_id].append(item)

    now = timezone.now()

    with transaction.atomic():
        result_units_by_inventory_item = {}

        for inventory_item_id, grouped_items in items_by_inventory_item.items():
            total_quantity = sum(
                (
                    _to_decimal(item.quantity)
                    for item in grouped_items
                ),
                ZERO,
            )

            source_unit = grouped_items[0].source_warehouse_unit

            result_unit = WarehouseUnit.objects.create(
                inventory_item_id=inventory_item_id,
                location=None,
                storage_place=None,
                quantity=total_quantity,
                source_receipt_item_id=source_unit.source_receipt_item_id,
                source_order_item_id=source_unit.source_order_item_id,
                tolling_source_receipt_item_id=(
                    source_unit.tolling_source_receipt_item_id
                ),
                tolling_source_order_item_id=(
                    source_unit.tolling_source_order_item_id
                ),
                status=WarehouseUnit.Status.IN_PRODUCTION,
            )

            result_units_by_inventory_item[inventory_item_id] = result_unit

        source_units_to_update = []
        reservations_to_update = []
        items_to_update = []
        events_to_create = []

        for item in items:
            source_unit = item.source_warehouse_unit
            result_unit = result_units_by_inventory_item[
                item.inventory_item_id
            ]
            reservation = item.production_reservation

            source_quantity = _to_decimal(source_unit.quantity)
            move_quantity = _to_decimal(item.quantity)

            if move_quantity == source_quantity:
                source_unit.status = WarehouseUnit.Status.IN_PRODUCTION
                source_unit.quantity = source_quantity
            elif move_quantity < source_quantity:
                source_unit.quantity = source_quantity - move_quantity
                source_unit.status = WarehouseUnit.Status.ON_STOCK
            else:
                raise ValidationError(
                    "Кількість переміщення перевищує кількість складської одиниці."
                )

            source_units_to_update.append(source_unit)

            reservation.status = WarehouseProductionReservation.Status.TRANSFERRED
            reservation.transferred_at = now
            reservations_to_update.append(reservation)

            item.result_warehouse_unit = result_unit
            items_to_update.append(item)

            events_to_create.append(
                WarehouseUnitEvent(
                    operation_type=WarehouseUnitEvent.OperationType.PRODUCTION_TRANSFER,
                    source_unit=source_unit,
                    result_unit=result_unit,
                    quantity=move_quantity,
                    from_location=item.executed_source_location,
                    from_storage_place=item.executed_source_storage_place,
                    to_location=None,
                    to_storage_place=None,
                    created_by=created_by,
                )
            )

        WarehouseUnit.objects.bulk_update(
            source_units_to_update,
            [
                "quantity",
                "status",
                "updated_at",
            ],
        )

        WarehouseProductionReservation.objects.bulk_update(
            reservations_to_update,
            [
                "status",
                "transferred_at",
            ],
        )

        WarehouseProductionMovementItem.objects.bulk_update(
            items_to_update,
            [
                "result_warehouse_unit",
            ],
        )

        WarehouseUnitEvent.objects.bulk_create(
            events_to_create,
        )

        movement.status = WarehouseProductionMovement.Status.EXECUTED
        movement.executed_at = now
        movement.save(
            update_fields=[
                "status",
                "executed_at",
            ]
        )

        create_sales_order_event(
            sales_order=movement.production_order.sales_order,
            event_type=SalesOrderEvent.EventType.PRODUCTION_MOVEMENT_EXECUTED,
            source=SalesOrderEvent.Source.WAREHOUSE,
            title="Компоненти передано у виробництво",
            message=(
                f"Компоненти для етапу "
                f"{movement.production_order_step.sequence_number}: "
                f"{movement.production_order_step.name} "
                f"передано у виробництво."
            ),
            payload={
                "production_movement_id": movement.id,
                "production_order_id": movement.production_order_id,
                "production_order_step_id": (
                    movement.production_order_step_id
                ),
                "items_count": len(items),
            },
            created_by=created_by,
        )

    return movement