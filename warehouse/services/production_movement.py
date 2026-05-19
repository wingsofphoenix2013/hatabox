from collections import defaultdict

from django.db import transaction
from rest_framework.exceptions import ValidationError

from production.models import ProductionOrderStep
from warehouse.models import (
    WarehouseProductionMovement,
    WarehouseProductionMovementItem,
    WarehouseProductionReservation,
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