from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from sales.models import SalesOrder, SalesOrderComponent

from warehouse.models import (
    MovementPlan,
    MovementPlanItem,
    WarehouseProductionReservation,
    WarehouseUnit,
)


ZERO = Decimal("0.000")


def _to_decimal(value) -> Decimal:
    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def _get_available_units_for_component(
    *,
    sales_order,
    component,
):
    reserved_movement_unit_ids = set(
        MovementPlanItem.objects.filter(
            plan__status=MovementPlan.Status.ACTIVE,
            is_reserved=True,
        ).values_list("warehouse_unit_id", flat=True)
    )

    queryset = WarehouseUnit.objects.select_related(
        "tolling_source_order_item",
        "tolling_source_order_item__order",
    ).filter(
        inventory_item_id=component.inv_item_id,
        status=WarehouseUnit.Status.ON_STOCK,
    ).exclude(
        id__in=reserved_movement_unit_ids,
    ).exclude(
        production_reservations__status=WarehouseProductionReservation.Status.ACTIVE,
    ).order_by(
        "created_at",
        "id",
    )

    if component.fulfillment_mode == SalesOrderComponent.FulfillmentMode.CUSTOMER:
        queryset = queryset.filter(
            tolling_source_order_item__order__organization_id=sales_order.organization_id,
        )

    elif component.fulfillment_mode == SalesOrderComponent.FulfillmentMode.MIXED:
        queryset = queryset.exclude(
            tolling_source_order_item__order__organization_id=sales_order.organization_id,
        )

    return list(queryset)


def reserve_for_sales_order(
    *,
    sales_order,
    created_by=None,
):
    if sales_order.status != SalesOrder.Status.DRAFT:
        raise ValidationError(
            "Резервування доступне лише для SalesOrder у статусі draft."
        )

    existing_active_reservations = WarehouseProductionReservation.objects.filter(
        sales_order=sales_order,
        status=WarehouseProductionReservation.Status.ACTIVE,
    ).exists()

    if existing_active_reservations:
        raise ValidationError(
            "Для цього SalesOrder вже існують активні резервування."
        )

    components = list(
        sales_order.components.select_related(
            "inv_item",
        ).all()
    )

    reservation_plan = []
    insufficient_required_components = []

    for component in components:
        required_quantity = _to_decimal(component.quantity)
        remaining_quantity = required_quantity

        units = _get_available_units_for_component(
            sales_order=sales_order,
            component=component,
        )

        component_reservations = []

        exact_match_unit = next(
            (
                unit
                for unit in units
                if _to_decimal(unit.quantity) == remaining_quantity
            ),
            None,
        )

        if exact_match_unit is not None:
            component_reservations.append({
                "warehouse_unit": exact_match_unit,
                "quantity": remaining_quantity,
            })
            remaining_quantity = ZERO

        else:
            fractional_units = [
                unit
                for unit in units
                if _to_decimal(unit.quantity) < required_quantity
            ]

            collected_quantity = ZERO
            fractional_reservations = []

            for unit in fractional_units:
                unit_quantity = _to_decimal(unit.quantity)

                if collected_quantity + unit_quantity > required_quantity:
                    continue

                fractional_reservations.append({
                    "warehouse_unit": unit,
                    "quantity": unit_quantity,
                })

                collected_quantity += unit_quantity

                if collected_quantity == required_quantity:
                    break

            if collected_quantity == required_quantity:
                component_reservations.extend(fractional_reservations)
                remaining_quantity = ZERO

            elif component.inv_item.is_splittable:
                larger_unit = next(
                    (
                        unit
                        for unit in units
                        if _to_decimal(unit.quantity) > remaining_quantity
                    ),
                    None,
                )

                if larger_unit is not None:
                    component_reservations.append({
                        "warehouse_unit": larger_unit,
                        "quantity": remaining_quantity,
                    })
                    remaining_quantity = ZERO

        reserved_quantity = required_quantity - remaining_quantity

        if (
            component.is_required_for_start
            and reserved_quantity < required_quantity
        ):
            insufficient_required_components.append({
                "component_id": component.id,
                "required_quantity": required_quantity,
                "reserved_quantity": reserved_quantity,
                "missing_quantity": required_quantity - reserved_quantity,
            })

        reservation_plan.append({
            "component": component,
            "required_quantity": required_quantity,
            "reserved_quantity": reserved_quantity,
            "missing_quantity": required_quantity - reserved_quantity,
            "reservations": component_reservations,
            "is_fully_reserved": reserved_quantity == required_quantity,
        })

    if insufficient_required_components:
        raise ValidationError({
            "required_components": insufficient_required_components,
        })

    with transaction.atomic():
        reservations_to_create = []
        units_to_update = []

        for row in reservation_plan:
            component = row["component"]

            for reservation_data in row["reservations"]:
                warehouse_unit = reservation_data["warehouse_unit"]

                warehouse_unit.status = WarehouseUnit.Status.BLOCKED
                units_to_update.append(warehouse_unit)

                reservations_to_create.append(
                    WarehouseProductionReservation(
                        warehouse_unit=warehouse_unit,
                        sales_order=sales_order,
                        sales_order_component=component,
                        quantity=reservation_data["quantity"],
                        status=WarehouseProductionReservation.Status.ACTIVE,
                        created_by=created_by,
                    )
                )

        if units_to_update:
            WarehouseUnit.objects.bulk_update(
                units_to_update,
                ["status"],
            )

        if reservations_to_create:
            WarehouseProductionReservation.objects.bulk_create(
                reservations_to_create,
            )

    return {
        "sales_order_id": sales_order.id,
        "components": [
            {
                "component_id": row["component"].id,
                "required_quantity": row["required_quantity"],
                "reserved_quantity": row["reserved_quantity"],
                "missing_quantity": row["missing_quantity"],
                "is_fully_reserved": row["is_fully_reserved"],
            }
            for row in reservation_plan
        ],
    }