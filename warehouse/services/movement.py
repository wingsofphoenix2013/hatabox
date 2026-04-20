from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Union

from rest_framework.exceptions import ValidationError
from django.db import transaction

from warehouse.models import WarehouseUnit, WarehouseUnitEvent


THREE_DECIMAL_PLACES = Decimal("0.001")


@dataclass(frozen=True)
class MovePlan:
    inventory_item_id: int
    requested_quantity: Decimal
    full_units: List[WarehouseUnit]
    split_source_unit: Optional[WarehouseUnit]
    split_move_quantity: Optional[Decimal]
    split_remainder_quantity: Optional[Decimal]
    
    @property
    def requires_split(self) -> bool:
        return self.split_source_unit is not None

    @property
    def total_full_units_quantity(self) -> Decimal:
        return sum((unit.quantity for unit in self.full_units), Decimal("0.000"))

@dataclass(frozen=True)
class MoveExecutionResult:
    move_plan: MovePlan
    moved_units: List[WarehouseUnit]
    created_unit: Optional[WarehouseUnit]
    split_source_unit: Optional[WarehouseUnit]


@dataclass(frozen=True)
class BulkMoveExecutionResult:
    moved_units: List[WarehouseUnit]


def _normalize_quantity(
    quantity: Union[Decimal, int, float, str]
) -> Decimal:
    try:
        normalized = Decimal(str(quantity)).quantize(
            THREE_DECIMAL_PLACES,
            rounding=ROUND_HALF_UP,
        )
    except (ArithmeticError, ValueError, TypeError) as exc:
        raise ValidationError({
            "quantity": "Некоректне значення кількості."
        }) from exc

    if normalized <= 0:
        raise ValidationError({
            "quantity": "Кількість повинна бути більше 0."
        })

    return normalized


def _to_millis(quantity: Decimal) -> int:
    normalized = quantity.quantize(
        THREE_DECIMAL_PLACES,
        rounding=ROUND_HALF_UP,
    )
    return int(normalized * 1000)


def _get_available_units(inventory_item) -> List[WarehouseUnit]:
    return list(
        WarehouseUnit.objects.filter(
            inventory_item=inventory_item,
            is_active=True,
        ).order_by("-quantity", "id")
    )


def _build_reachable_sums(
    units: List[WarehouseUnit],
    limit_millis: int,
) -> Dict[int, List[WarehouseUnit]]:
    reachable: Dict[int, List[WarehouseUnit]] = {0: []}

    for unit in units:
        unit_millis = _to_millis(unit.quantity)
        current_items = sorted(reachable.items(), reverse=True)

        for current_sum, current_units in current_items:
            new_sum = current_sum + unit_millis
            if new_sum > limit_millis:
                continue

            candidate_units = current_units + [unit]
            existing_units = reachable.get(new_sum)

            if existing_units is None:
                reachable[new_sum] = candidate_units
                continue

            existing_signature = (
                len(existing_units),
                sum((_to_millis(item.quantity) for item in existing_units)),
                [item.id for item in existing_units],
            )
            candidate_signature = (
                len(candidate_units),
                sum((_to_millis(item.quantity) for item in candidate_units)),
                [item.id for item in candidate_units],
            )

            if candidate_signature < existing_signature:
                reachable[new_sum] = candidate_units

    return reachable


def _find_exact_units(
    units: List[WarehouseUnit],
    target_millis: int,
) -> Optional[List[WarehouseUnit]]:
    reachable = _build_reachable_sums(
        units=units,
        limit_millis=target_millis,
    )
    return reachable.get(target_millis)


def _apply_destination(
    unit: WarehouseUnit,
    target_location=None,
    target_storage_place=None,
) -> None:
    if target_location is not None:
        unit.location = target_location
        unit.storage_place = None
    else:
        unit.location = None
        unit.storage_place = target_storage_place


def _validate_destination(
    target_location=None,
    target_storage_place=None,
) -> None:
    if (target_location is None) == (target_storage_place is None):
        raise ValidationError({
            "destination": (
                "Потрібно вказати або target_location, або target_storage_place, "
                "але не обидва одночасно."
            )
        })

    if target_location is not None and not target_location.is_active:
        raise ValidationError({
            "target_location": "Неможливо перемістити в неактивну локацію."
        })

    if target_storage_place is not None and not target_storage_place.is_active:
        raise ValidationError({
            "target_storage_place": (
                "Неможливо перемістити в неактивне місце зберігання."
            )
        })


def _is_same_destination(
    unit: WarehouseUnit,
    target_location=None,
    target_storage_place=None,
) -> bool:
    if target_location is not None:
        return unit.location_id == target_location.id and unit.storage_place_id is None

    return unit.storage_place_id == target_storage_place.id and unit.location_id is None


def plan_move(
    inventory_item,
    quantity: Union[Decimal, int, float, str],
) -> MovePlan:
    requested_quantity = _normalize_quantity(quantity)
    target_millis = _to_millis(requested_quantity)

    available_units = _get_available_units(inventory_item)
    if not available_units:
        raise ValidationError(
            "Немає доступних складських одиниць для цього товару."
        )

    total_available_millis = sum(
        _to_millis(unit.quantity)
        for unit in available_units
    )
    if total_available_millis < target_millis:
        raise ValidationError({
            "quantity": "Недостатньо доступної кількості для переміщення."
        })

    exact_units = _find_exact_units(
        units=available_units,
        target_millis=target_millis,
    )
    if exact_units is not None:
        return MovePlan(
            inventory_item_id=inventory_item.id,
            requested_quantity=requested_quantity,
            full_units=exact_units,
            split_source_unit=None,
            split_move_quantity=None,
            split_remainder_quantity=None,
        )

    if not inventory_item.is_splittable:
        raise ValidationError({
            "quantity": (
                "Для цього товару часткове переміщення неможливе: "
                "потрібне розділення складської одиниці, але item не є splittable."
            )
        })

    units_for_split = sorted(
        available_units,
        key=lambda unit: (_to_millis(unit.quantity), unit.id),
    )

    for split_source_unit in units_for_split:
        split_source_millis = _to_millis(split_source_unit.quantity)

        if split_source_millis <= 1:
            continue

        other_units = [
            unit
            for unit in available_units
            if unit.id != split_source_unit.id
        ]

        reachable = _build_reachable_sums(
            units=other_units,
            limit_millis=target_millis - 1,
        )

        valid_base_sums = [
            base_sum
            for base_sum in reachable.keys()
            if 0 <= base_sum < target_millis
            and 0 < (target_millis - base_sum) < split_source_millis
        ]

        if not valid_base_sums:
            continue

        best_base_sum = max(valid_base_sums)
        full_units = reachable[best_base_sum]

        split_move_millis = target_millis - best_base_sum
        split_remainder_millis = split_source_millis - split_move_millis

        return MovePlan(
            inventory_item_id=inventory_item.id,
            requested_quantity=requested_quantity,
            full_units=full_units,
            split_source_unit=split_source_unit,
            split_move_quantity=Decimal(split_move_millis) / Decimal("1000"),
            split_remainder_quantity=Decimal(split_remainder_millis) / Decimal("1000"),
        )

    raise ValidationError({
        "quantity": (
            "Не знайдено підходящої складської одиниці для часткового переміщення. "
            "Потрібне розділення, але жодна доступна одиниця не підходить."
        )
    })


def execute_move(
    inventory_item,
    quantity: Union[Decimal, int, float, str],
    target_location=None,
    target_storage_place=None,
    created_by=None,
) -> MoveExecutionResult:
    _validate_destination(
        target_location=target_location,
        target_storage_place=target_storage_place,
    )

    move_plan = plan_move(
        inventory_item=inventory_item,
        quantity=quantity,
    )

    same_destination_unit_ids = [
        unit.id
        for unit in move_plan.full_units
        if _is_same_destination(
            unit,
            target_location=target_location,
            target_storage_place=target_storage_place,
        )
    ]
    if same_destination_unit_ids:
        raise ValidationError({
            "destination": (
                "Неможливо перемістити складські одиниці в те саме місце. "
                f"Unit id: {same_destination_unit_ids}"
            )
        })

    if move_plan.split_source_unit is not None and _is_same_destination(
        move_plan.split_source_unit,
        target_location=target_location,
        target_storage_place=target_storage_place,
    ):
        raise ValidationError({
            "destination": (
                "Неможливо перемістити складську одиницю в те саме місце."
            )
        })

    moved_units: List[WarehouseUnit] = []
    created_unit: Optional[WarehouseUnit] = None
    split_source_unit: Optional[WarehouseUnit] = None

    with transaction.atomic():
        for unit in move_plan.full_units:
            from_location = unit.location
            from_storage_place = unit.storage_place

            _apply_destination(
                unit,
                target_location=target_location,
                target_storage_place=target_storage_place,
            )
            unit.save()
            moved_units.append(unit)

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

        if move_plan.requires_split:
            split_source_unit = move_plan.split_source_unit
            from_location = split_source_unit.location
            from_storage_place = split_source_unit.storage_place

            split_source_unit.quantity = move_plan.split_remainder_quantity
            split_source_unit.save()

            created_unit = WarehouseUnit(
                inventory_item=split_source_unit.inventory_item,
                location=None,
                storage_place=None,
                quantity=move_plan.split_move_quantity,
                source_receipt_item=split_source_unit.source_receipt_item,
                source_order_item=split_source_unit.source_order_item,
                is_active=split_source_unit.is_active,
            )
            _apply_destination(
                created_unit,
                target_location=target_location,
                target_storage_place=target_storage_place,
            )
            created_unit.save()
            moved_units.append(created_unit)

            WarehouseUnitEvent.objects.create(
                operation_type=WarehouseUnitEvent.OperationType.SPLIT_MOVE,
                source_unit=split_source_unit,
                result_unit=created_unit,
                quantity=created_unit.quantity,
                from_location=from_location,
                from_storage_place=from_storage_place,
                to_location=created_unit.location,
                to_storage_place=created_unit.storage_place,
                created_by=created_by,
            )

    return MoveExecutionResult(
        move_plan=move_plan,
        moved_units=moved_units,
        created_unit=created_unit,
        split_source_unit=split_source_unit,
    )

def execute_bulk_move(
    unit_ids: List[int],
    target_location=None,
    target_storage_place=None,
    created_by=None,
) -> BulkMoveExecutionResult:
    _validate_destination(
        target_location=target_location,
        target_storage_place=target_storage_place,
    )

    if not unit_ids:
        raise ValidationError({
            "unit_ids": "Потрібно передати хоча б одну складську одиницю."
        })

    units = list(
        WarehouseUnit.objects.filter(id__in=unit_ids).order_by("id")
    )

    found_ids = {unit.id for unit in units}
    missing_ids = [unit_id for unit_id in unit_ids if unit_id not in found_ids]
    if missing_ids:
        raise ValidationError({
            "unit_ids": f"Не знайдено складські одиниці з id: {missing_ids}"
        })

    inactive_ids = [unit.id for unit in units if not unit.is_active]
    if inactive_ids:
        raise ValidationError({
            "unit_ids": (
                f"Неможливо перемістити неактивні складські одиниці: {inactive_ids}"
            )
        })

    same_destination_ids = [
        unit.id
        for unit in units
        if _is_same_destination(
            unit,
            target_location=target_location,
            target_storage_place=target_storage_place,
        )
    ]
    if same_destination_ids:
        raise ValidationError({
            "unit_ids": (
                "Неможливо перемістити складські одиниці в те саме місце. "
                f"Unit id: {same_destination_ids}"
            )
        })

    with transaction.atomic():
        for unit in units:
            from_location = unit.location
            from_storage_place = unit.storage_place

            _apply_destination(
                unit,
                target_location=target_location,
                target_storage_place=target_storage_place,
            )
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

    return BulkMoveExecutionResult(
        moved_units=units,
    )