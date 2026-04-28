from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Union

from rest_framework.exceptions import ValidationError

from warehouse.models import (
    MovementPlan,
    MovementPlanItem,
    WarehouseUnit,
)


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
    reserved_unit_ids = MovementPlanItem.objects.filter(
        plan__status=MovementPlan.Status.ACTIVE,
        is_reserved=True,
    ).values_list("warehouse_unit_id", flat=True)

    return list(
        WarehouseUnit.objects.filter(
            inventory_item=inventory_item,
            is_active=True,
        ).exclude(
            id__in=reserved_unit_ids,
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


def _find_sequential_exact_units(
    units: List[WarehouseUnit],
    target_millis: int,
) -> Optional[List[WarehouseUnit]]:
    selected_units = []
    selected_sum = 0

    for unit in units:
        selected_sum += _to_millis(unit.quantity)
        selected_units.append(unit)

        if selected_sum == target_millis:
            return selected_units

        if selected_sum > target_millis:
            return None

    return None


def _find_exact_units(
    units: List[WarehouseUnit],
    target_millis: int,
) -> Optional[List[WarehouseUnit]]:
    sequential_units = _find_sequential_exact_units(
        units=units,
        target_millis=target_millis,
    )
    if sequential_units is not None:
        return sequential_units

    reachable = _build_reachable_sums(
        units=units,
        limit_millis=target_millis,
    )
    return reachable.get(target_millis)


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
