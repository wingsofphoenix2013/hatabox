from typing import Optional

from django.db import transaction
from rest_framework.exceptions import ValidationError

from warehouse.models import (
    MovementPlan,
    WarehouseLocation,
    WarehouseStoragePlace,
    MovementPlanItem,
    WarehouseUnit,
    WarehouseUnitEvent,
)
from warehouse.services.movement import plan_move


def _validate_destination(
    target_location: Optional[WarehouseLocation],
    target_storage_place: Optional[WarehouseStoragePlace],
):
    if (target_location is None) == (target_storage_place is None):
        raise ValidationError(
            "Потрібно вказати або target_location, або target_storage_place, але не обидва одночасно."
        )

    if target_location is not None and not target_location.is_active:
        raise ValidationError("Неможливо створити план для неактивної локації.")

    if target_storage_place is not None and not target_storage_place.is_active:
        raise ValidationError("Неможливо створити план для неактивного місця зберігання.")


def create_movement_plan(
    *,
    target_location: Optional[WarehouseLocation] = None,
    target_storage_place: Optional[WarehouseStoragePlace] = None,
    created_by=None,
    planned_at=None,
) -> MovementPlan:
    _validate_destination(
        target_location=target_location,
        target_storage_place=target_storage_place,
    )

    with transaction.atomic():
        plan = MovementPlan.objects.create(
            status=MovementPlan.Status.DRAFT,
            target_location=target_location,
            target_storage_place=target_storage_place,
            created_by=created_by,
            planned_at=planned_at,
        )

    return plan


def add_items_to_plan(
    *,
    plan: MovementPlan,
    inventory_item,
    quantity,
) -> None:
    if plan.status not in [MovementPlan.Status.DRAFT, MovementPlan.Status.ACTIVE]:
        raise ValidationError("Можна додавати товари лише в draft або active план.")

    move_plan = plan_move(
        inventory_item=inventory_item,
        quantity=quantity,
    )

    with transaction.atomic():
        if plan.status == MovementPlan.Status.DRAFT:
            plan.status = MovementPlan.Status.ACTIVE
            plan.save(update_fields=["status"])

        units_to_reserve = list(move_plan.full_units)

        if move_plan.requires_split:
            units_to_reserve.append(move_plan.split_source_unit)

        # запрет: unit уже в destination
        same_destination_ids = [
            unit.id
            for unit in units_to_reserve
            if (
                plan.target_location is not None
                and unit.location_id == plan.target_location.id
                and unit.storage_place_id is None
            ) or (
                plan.target_storage_place is not None
                and unit.storage_place_id == plan.target_storage_place.id
                and unit.location_id is None
            )
        ]

        if same_destination_ids:
            raise ValidationError(
                f"Неможливо додати складські одиниці, які вже знаходяться у місці призначення: {same_destination_ids}"
            )

        # запрет: уже зарезервированы (в любом active плане)
        already_reserved_ids = list(
            MovementPlanItem.objects.filter(
                warehouse_unit__in=units_to_reserve,
                is_reserved=True,
            ).values_list("warehouse_unit_id", flat=True)
        )

        if already_reserved_ids:
            raise ValidationError(
                f"Деякі складські одиниці вже зарезервовані: {already_reserved_ids}"
            )

        # запрет: уже есть в текущем плане
        existing_in_plan_ids = list(
            MovementPlanItem.objects.filter(
                plan=plan,
                warehouse_unit__in=units_to_reserve,
            ).values_list("warehouse_unit_id", flat=True)
        )

        if existing_in_plan_ids:
            raise ValidationError(
                f"Деякі складські одиниці вже додані до цього плану: {existing_in_plan_ids}"
            )

        for unit in move_plan.full_units:
            MovementPlanItem.objects.create(
                plan=plan,
                warehouse_unit=unit,
                reserved_quantity=unit.quantity,
                requires_split=False,
            )

        if move_plan.requires_split:
            MovementPlanItem.objects.create(
                plan=plan,
                warehouse_unit=move_plan.split_source_unit,
                reserved_quantity=move_plan.split_source_unit.quantity,
                move_quantity=move_plan.split_move_quantity,
                remainder_quantity=move_plan.split_remainder_quantity,
                requires_split=True,
            )


def execute_movement_plan(
    *,
    plan: MovementPlan,
    created_by=None,
):
    if plan.status != MovementPlan.Status.ACTIVE:
        raise ValidationError("Можна виконати лише active план.")

    target_location = plan.target_location
    target_storage_place = plan.target_storage_place

    items = list(plan.items.all())

    if not items:
        raise ValidationError("План не містить жодної складської одиниці.")

    with transaction.atomic():
        MovementPlanItem.objects.filter(
            plan=plan,
            is_reserved=True,
        ).update(is_reserved=False)

        plan.status = MovementPlan.Status.EXECUTED
        plan.save(update_fields=["status"])

        for item in items:
            unit = item.warehouse_unit

            from_location = unit.location
            from_storage_place = unit.storage_place

            if item.requires_split:
                unit.quantity = item.remainder_quantity
                unit.save()

                created_unit = WarehouseUnit(
                    inventory_item=unit.inventory_item,
                    location=None,
                    storage_place=None,
                    quantity=item.move_quantity,
                    source_receipt_item=unit.source_receipt_item,
                    source_order_item=unit.source_order_item,
                    tolling_source_receipt_item=unit.tolling_source_receipt_item,
                    tolling_source_order_item=unit.tolling_source_order_item,
                    is_active=unit.is_active,
                )

                if target_location is not None:
                    created_unit.location = target_location
                else:
                    created_unit.storage_place = target_storage_place

                created_unit.save()

                WarehouseUnitEvent.objects.create(
                    operation_type=WarehouseUnitEvent.OperationType.SPLIT_MOVE,
                    source_unit=unit,
                    result_unit=created_unit,
                    quantity=created_unit.quantity,
                    from_location=from_location,
                    from_storage_place=from_storage_place,
                    to_location=created_unit.location,
                    to_storage_place=created_unit.storage_place,
                    created_by=created_by,
                )

            else:
                if target_location is not None:
                    unit.location = target_location
                    unit.storage_place = None
                else:
                    unit.location = None
                    unit.storage_place = target_storage_place

                unit.save()

                WarehouseUnitEvent.objects.create(
                    operation_type=WarehouseUnitEvent.OperationType.MOVE,
                    source_unit=unit,
                    result_unit=unit,
                    quantity=unit.quantity,
                    from_location=from_location,
                    from_storage_place=from_storage_place,
                    to_location=unit.location,
                    to_storage_place=unit.storage_place,
                    created_by=created_by,
                )


def cancel_movement_plan(
    *,
    plan: MovementPlan,
) -> None:
    if plan.status not in [MovementPlan.Status.DRAFT, MovementPlan.Status.ACTIVE]:
        raise ValidationError("Можна скасувати лише draft або active план.")

    with transaction.atomic():
        MovementPlanItem.objects.filter(
            plan=plan,
            is_reserved=True,
        ).update(is_reserved=False)

        plan.status = MovementPlan.Status.CANCELLED
        plan.save(update_fields=["status"])