from typing import Optional

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
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
from warehouse.services.movement_plan_invoice import is_movement_plan_invoice_actual


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
    comment="",
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
            comment=comment,
        )

    return plan

def update_movement_plan(
    *,
    plan: MovementPlan,
    target_location=None,
    target_storage_place=None,
    planned_at=None,
    comment=None,
    destination_provided=False,
):
    if plan.status not in [MovementPlan.Status.DRAFT, MovementPlan.Status.ACTIVE]:
        raise ValidationError("Можна редагувати лише draft або active план.")

    if planned_at is not None:
        planned_date = timezone.localtime(planned_at).date()
        today = timezone.localdate()

        if planned_date < today:
            raise ValidationError({
                "planned_at": "Планова дата не може бути в минулому."
            })

    if plan.status == MovementPlan.Status.ACTIVE and destination_provided:
        raise ValidationError(
            "Неможливо змінювати місце призначення для active плану."
        )

    with transaction.atomic():
        if plan.status == MovementPlan.Status.DRAFT and destination_provided:
            _validate_destination(
                target_location=target_location,
                target_storage_place=target_storage_place,
            )
            plan.target_location = target_location
            plan.target_storage_place = target_storage_place

        if planned_at is not None:
            plan.planned_at = planned_at

        if comment is not None:
            plan.comment = comment

        plan.save()

    return plan

def remove_item_from_plan(
    *,
    plan: MovementPlan,
    item_id: int,
):
    if plan.status != MovementPlan.Status.ACTIVE:
        raise ValidationError("Можна видаляти рядки лише з active плану.")

    try:
        item = MovementPlanItem.objects.get(
            id=item_id,
            plan=plan,
        )
    except MovementPlanItem.DoesNotExist:
        raise ValidationError("Рядок плану не знайдено.")

    with transaction.atomic():
        if item.is_reserved:
            item.is_reserved = False
            item.save(update_fields=["is_reserved"])

        item.delete()

        remaining_items_exists = MovementPlanItem.objects.filter(
            plan=plan,
            is_reserved=True,
        ).exists()

        if not remaining_items_exists:
            plan.status = MovementPlan.Status.CANCELLED
            plan.save(update_fields=["status"])

    return {
        "status": "ok",
        "plan_status": plan.status,
    }
    
def change_plan_item_quantity(
    *,
    plan: MovementPlan,
    item_id: int,
    quantity,
):
    if plan.status != MovementPlan.Status.ACTIVE:
        raise ValidationError("Можна змінювати кількість лише в active плані.")

    try:
        item = MovementPlanItem.objects.select_related(
            "warehouse_unit",
            "warehouse_unit__inventory_item",
        ).get(
            id=item_id,
            plan=plan,
        )
    except MovementPlanItem.DoesNotExist:
        raise ValidationError("Рядок плану не знайдено.")

    inventory_item = item.warehouse_unit.inventory_item

    with transaction.atomic():
        if item.is_reserved:
            item.is_reserved = False
            item.save(update_fields=["is_reserved"])

        item.delete()

        add_items_to_plan(
            plan=plan,
            inventory_item=inventory_item,
            quantity=quantity,
        )

    return plan
    
def change_inventory_item_quantity_in_plan(
    *,
    plan: MovementPlan,
    inventory_item,
    quantity,
):
    if plan.status != MovementPlan.Status.ACTIVE:
        raise ValidationError("Можна змінювати кількість лише в active плані.")

    with transaction.atomic():
        _delete_plan_inventory_item_reservations(
            plan=plan,
            inventory_item=inventory_item,
        )

        add_items_to_plan(
            plan=plan,
            inventory_item=inventory_item,
            quantity=quantity,
        )

    return plan
    
def remove_inventory_item_from_plan(
    *,
    plan: MovementPlan,
    inventory_item,
):
    if plan.status != MovementPlan.Status.ACTIVE:
        raise ValidationError("Можна видаляти лише з active плану.")

    with transaction.atomic():
        _delete_plan_inventory_item_reservations(
            plan=plan,
            inventory_item=inventory_item,
        )

        has_items = MovementPlanItem.objects.filter(
            plan=plan,
            is_reserved=True,
        ).exists()

        if not has_items:
            plan.status = MovementPlan.Status.CANCELLED
            plan.save(update_fields=["status"])

    return {
        "status": "ok",
        "plan_status": plan.status,
    }

def _get_plan_inventory_item_quantity(
    *,
    plan: MovementPlan,
    inventory_item,
):
    total = 0

    for item in MovementPlanItem.objects.select_related(
        "warehouse_unit",
        "warehouse_unit__inventory_item",
    ).filter(
        plan=plan,
        warehouse_unit__inventory_item=inventory_item,
    ):
        if item.requires_split:
            total += item.move_quantity
        else:
            total += item.reserved_quantity

    return total


def _delete_plan_inventory_item_reservations(
    *,
    plan: MovementPlan,
    inventory_item,
):
    items = MovementPlanItem.objects.filter(
        plan=plan,
        warehouse_unit__inventory_item=inventory_item,
    )

    items.update(is_reserved=False)
    items.delete()

def add_items_to_plan(
    *,
    plan: MovementPlan,
    inventory_item,
    quantity,
) -> None:
    if plan.status not in [MovementPlan.Status.DRAFT, MovementPlan.Status.ACTIVE]:
        raise ValidationError("Можна додавати товари лише в draft або active план.")

    current_quantity = _get_plan_inventory_item_quantity(
        plan=plan,
        inventory_item=inventory_item,
    )
    target_quantity = current_quantity + quantity

    _delete_plan_inventory_item_reservations(
        plan=plan,
        inventory_item=inventory_item,
    )

    same_destination_unit_ids = list(
        WarehouseUnit.objects.filter(
            inventory_item=inventory_item,
            is_active=True,
        ).filter(
            (
                Q(
                    location=plan.target_location,
                    storage_place__isnull=True,
                )
                if plan.target_location is not None
                else Q(
                    location__isnull=True,
                    storage_place=plan.target_storage_place,
                )
            )
        ).values_list("id", flat=True)
    )

    move_plan = plan_move(
        inventory_item=inventory_item,
        quantity=target_quantity,
        exclude_unit_ids=same_destination_unit_ids,
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

    if not is_movement_plan_invoice_actual(plan):
        raise ValidationError(
            "Накладна застаріла або відсутня. Оновіть PDF перед виконанням переміщення."
        )

    target_location = plan.target_location
    target_storage_place = plan.target_storage_place

    items = list(
        MovementPlanItem.objects.select_related(
            "warehouse_unit",
            "warehouse_unit__location",
            "warehouse_unit__storage_place",
        ).filter(
            plan=plan,
        )
    )

    if not items:
        raise ValidationError("План не містить жодної складської одиниці.")

    with transaction.atomic():
        MovementPlanItem.objects.filter(
            plan=plan,
            is_reserved=True,
        ).update(is_reserved=False)

        plan.status = MovementPlan.Status.EXECUTED
        plan.save(update_fields=["status"])

        units_to_update = []
        move_events_to_create = []

        for item in items:
            unit = item.warehouse_unit

            from_location = unit.location
            from_storage_place = unit.storage_place

            # snapshot исходного размещения
            if from_storage_place is not None:
                src_location = from_storage_place.location
                item.executed_source_location = src_location
                item.executed_source_location_code = src_location.code
                item.executed_source_location_name = src_location.name

                item.executed_source_storage_place = from_storage_place
                item.executed_source_storage_place_code = from_storage_place.code
                item.executed_source_storage_place_display_name = from_storage_place.get_display_name()
                item.executed_source_storage_place_full_display = from_storage_place.get_display_name_verbose()
            else:
                src_location = from_location
                item.executed_source_location = src_location
                item.executed_source_location_code = src_location.code
                item.executed_source_location_name = src_location.name

                item.executed_source_storage_place = None
                item.executed_source_storage_place_code = ""
                item.executed_source_storage_place_display_name = ""
                item.executed_source_storage_place_full_display = ""

            item.save(update_fields=[
                "executed_source_location",
                "executed_source_location_code",
                "executed_source_location_name",
                "executed_source_storage_place",
                "executed_source_storage_place_code",
                "executed_source_storage_place_display_name",
                "executed_source_storage_place_full_display",
            ])

            if item.requires_split:
                unit.quantity = item.remainder_quantity
                WarehouseUnit.objects.filter(pk=unit.pk).update(
                    quantity=unit.quantity,
                    updated_at=timezone.now(),
                )
                unit.refresh_from_db(fields=["quantity"])

                created_unit = WarehouseUnit(
                    inventory_item_id=unit.inventory_item_id,
                    location=None,
                    storage_place=None,
                    quantity=item.move_quantity,
                    source_receipt_item_id=unit.source_receipt_item_id,
                    source_order_item_id=unit.source_order_item_id,
                    tolling_source_receipt_item_id=unit.tolling_source_receipt_item_id,
                    tolling_source_order_item_id=unit.tolling_source_order_item_id,
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

                continue

            if target_location is not None:
                unit.location = target_location
                unit.storage_place = None
            else:
                unit.location = None
                unit.storage_place = target_storage_place

            units_to_update.append(unit)

            move_events_to_create.append(
                WarehouseUnitEvent(
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
            )

        if units_to_update:
            WarehouseUnit.objects.bulk_update(
                units_to_update,
                ["location", "storage_place"],
            )

        if move_events_to_create:
            WarehouseUnitEvent.objects.bulk_create(move_events_to_create)

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