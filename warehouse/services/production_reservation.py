from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from organizations.models import Organization
from sales.models import SalesOrder, SalesOrderComponent

from production.models import ProductionOrderStep
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


def _build_available_unit_pools(
    *,
    sales_order,
    item_ids,
):
    reserved_movement_unit_ids = set(
        MovementPlanItem.objects.filter(
            plan__status=MovementPlan.Status.ACTIVE,
            is_reserved=True,
        ).values_list("warehouse_unit_id", flat=True)
    )

    units_queryset = (
        WarehouseUnit.objects.select_related(
            "tolling_source_order_item",
            "tolling_source_order_item__order",
        ).filter(
            inventory_item_id__in=item_ids,
            status=WarehouseUnit.Status.ON_STOCK,
        ).exclude(
            id__in=reserved_movement_unit_ids,
        ).exclude(
            production_reservations__status=WarehouseProductionReservation.Status.ACTIVE,
        ).order_by(
            "created_at",
            "id",
        )
    )

    if transaction.get_connection().in_atomic_block:
        units_queryset = units_queryset.select_for_update(of=("self",))

    units = list(units_queryset)

    pools = defaultdict(lambda: {
        "customer": [],
        "donor": [],
        "own": [],
    })

    for unit in units:
        if unit.tolling_source_order_item_id:
            organization = unit.tolling_source_order_item.order.organization

            if organization.id == sales_order.organization_id:
                pools[unit.inventory_item_id]["customer"].append(unit)
            elif organization.type == Organization.Type.CHARITY:
                pools[unit.inventory_item_id]["donor"].append(unit)

            continue

        if unit.source_order_item_id:
            pools[unit.inventory_item_id]["own"].append(unit)

    return pools


def _select_units_from_pool(
    *,
    units,
    required_quantity,
    allow_larger_splittable_unit,
):
    remaining_quantity = required_quantity
    selected = []

    exact_match_unit = next(
        (
            unit
            for unit in units
            if _to_decimal(unit.quantity) == remaining_quantity
        ),
        None,
    )

    if exact_match_unit is not None:
        return [
            {
                "warehouse_unit": exact_match_unit,
                "quantity": remaining_quantity,
            }
        ], ZERO

    collected_quantity = ZERO
    fractional_selected = []

    for unit in units:
        unit_quantity = _to_decimal(unit.quantity)

        if unit_quantity >= required_quantity:
            continue

        if collected_quantity + unit_quantity > required_quantity:
            continue

        fractional_selected.append({
            "warehouse_unit": unit,
            "quantity": unit_quantity,
        })

        collected_quantity += unit_quantity

        if collected_quantity == required_quantity:
            return fractional_selected, ZERO

    if fractional_selected:
        selected.extend(fractional_selected)
        remaining_quantity -= collected_quantity

    if allow_larger_splittable_unit and remaining_quantity > ZERO:
        used_unit_ids = {
            row["warehouse_unit"].id
            for row in selected
        }

        larger_unit = next(
            (
                unit
                for unit in units
                if unit.id not in used_unit_ids
                and _to_decimal(unit.quantity) > remaining_quantity
            ),
            None,
        )

        if larger_unit is not None:
            selected.append({
                "warehouse_unit": larger_unit,
                "quantity": remaining_quantity,
            })
            remaining_quantity = ZERO

    return selected, remaining_quantity

def reserve_components_for_production_step_confirmation(
    *,
    production_order_step,
    created_by=None,
):
    if production_order_step.status != ProductionOrderStep.Status.DRAFT:
        raise ValidationError(
            "Підтвердити можна лише етап у статусі draft."
        )

    sales_order = production_order_step.production_order.sales_order

    step_components = list(
        production_order_step.components.select_related(
            "inv_item",
            "sales_order_component",
        ).order_by(
            "id",
        )
    )

    if not step_components:
        return {
            "production_order_step_id": production_order_step.id,
            "components": [],
            "inv_item_ids": [],
        }

    existing_step_reservations = WarehouseProductionReservation.objects.filter(
        production_order_step_component__in=step_components,
        status=WarehouseProductionReservation.Status.ACTIVE,
    ).exists()

    if existing_step_reservations:
        raise ValidationError(
            "Для цього етапу вже існують активні резервування."
        )

    item_ids = [
        component.inv_item_id
        for component in step_components
    ]

    available_unit_pools = _build_available_unit_pools(
        sales_order=sales_order,
        item_ids=item_ids,
    )

    reservation_plan = []
    insufficient_components = []

    for component in step_components:
        required_quantity = _to_decimal(component.required_quantity)
        sales_order_component = component.sales_order_component

        if (
            sales_order_component.fulfillment_mode
            == SalesOrderComponent.FulfillmentMode.CUSTOMER
        ):
            customer_reservations = list(
                WarehouseProductionReservation.objects.select_related(
                    "warehouse_unit",
                ).filter(
                    sales_order=sales_order,
                    sales_order_component=sales_order_component,
                    production_order_step_component__isnull=True,
                    status=WarehouseProductionReservation.Status.ACTIVE,
                ).order_by(
                    "created_at",
                    "id",
                )
            )

            selected_reservations = []
            remaining_quantity = required_quantity

            for reservation in customer_reservations:
                if _to_decimal(reservation.quantity) > remaining_quantity:
                    continue

                selected_reservations.append(reservation)
                remaining_quantity -= _to_decimal(reservation.quantity)

                if remaining_quantity == ZERO:
                    break

            if remaining_quantity > ZERO:
                insufficient_components.append({
                    "production_order_step_component_id": component.id,
                    "sales_order_component_id": sales_order_component.id,
                    "required_quantity": required_quantity,
                    "missing_quantity": remaining_quantity,
                })

            reservation_plan.append({
                "component": component,
                "mode": SalesOrderComponent.FulfillmentMode.CUSTOMER,
                "required_quantity": required_quantity,
                "missing_quantity": remaining_quantity,
                "customer_reservations": selected_reservations,
                "mixed_reservations": [],
            })

            continue

        selected_reservations, remaining_quantity = _select_units_from_pool(
            units=available_unit_pools[component.inv_item_id]["donor"],
            required_quantity=required_quantity,
            allow_larger_splittable_unit=False,
        )

        if remaining_quantity > ZERO:
            own_reservations, remaining_quantity = _select_units_from_pool(
                units=available_unit_pools[component.inv_item_id]["own"],
                required_quantity=remaining_quantity,
                allow_larger_splittable_unit=component.inv_item.is_splittable,
            )
            selected_reservations.extend(own_reservations)

        if remaining_quantity > ZERO:
            insufficient_components.append({
                "production_order_step_component_id": component.id,
                "sales_order_component_id": sales_order_component.id,
                "required_quantity": required_quantity,
                "missing_quantity": remaining_quantity,
            })

        reservation_plan.append({
            "component": component,
            "mode": SalesOrderComponent.FulfillmentMode.MIXED,
            "required_quantity": required_quantity,
            "missing_quantity": remaining_quantity,
            "customer_reservations": [],
            "mixed_reservations": selected_reservations,
        })

    if insufficient_components:
        raise ValidationError({
            "step_components": insufficient_components,
        })

    with transaction.atomic():
        reservations_to_update = []
        reservations_to_create = []
        units_to_update = []

        for row in reservation_plan:
            component = row["component"]

            if row["mode"] == SalesOrderComponent.FulfillmentMode.CUSTOMER:
                for reservation in row["customer_reservations"]:
                    reservation.production_order_step_component = component
                    reservations_to_update.append(reservation)

                continue

            for reservation_data in row["mixed_reservations"]:
                warehouse_unit = reservation_data["warehouse_unit"]

                warehouse_unit.status = WarehouseUnit.Status.BLOCKED
                units_to_update.append(warehouse_unit)

                reservations_to_create.append(
                    WarehouseProductionReservation(
                        warehouse_unit=warehouse_unit,
                        sales_order=sales_order,
                        sales_order_component=component.sales_order_component,
                        production_order_step_component=component,
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

        if reservations_to_update:
            WarehouseProductionReservation.objects.bulk_update(
                reservations_to_update,
                ["production_order_step_component"],
            )

        if reservations_to_create:
            WarehouseProductionReservation.objects.bulk_create(
                reservations_to_create,
            )

    return {
        "production_order_step_id": production_order_step.id,
        "components": [
            {
                "production_order_step_component_id": row["component"].id,
                "sales_order_component_id": row[
                    "component"
                ].sales_order_component_id,
                "inv_item_id": row["component"].inv_item_id,
                "required_quantity": row["required_quantity"],
                "missing_quantity": row["missing_quantity"],
                "fulfillment_mode": row["mode"],
            }
            for row in reservation_plan
        ],
        "inv_item_ids": list({
            row["component"].inv_item_id
            for row in reservation_plan
        }),
    }


def reserve_customer_components_for_confirmation(
    *,
    sales_order,
    created_by=None,
):
    existing_active_reservations = WarehouseProductionReservation.objects.filter(
        sales_order=sales_order,
        status=WarehouseProductionReservation.Status.ACTIVE,
    ).exists()

    if existing_active_reservations:
        raise ValidationError(
            "Для цього SalesOrder вже існують активні резервування."
        )

    customer_components = list(
        sales_order.components.select_related(
            "inv_item",
        ).filter(
            fulfillment_mode=SalesOrderComponent.FulfillmentMode.CUSTOMER,
        )
    )

    if not customer_components:
        return {
            "sales_order_id": sales_order.id,
            "components": [],
        }

    item_ids = [
        component.inv_item_id
        for component in customer_components
    ]

    available_unit_pools = _build_available_unit_pools(
        sales_order=sales_order,
        item_ids=item_ids,
    )

    reservation_plan = []
    insufficient_components = []

    for component in customer_components:
        required_quantity = _to_decimal(component.quantity)

        selected_reservations, remaining_quantity = _select_units_from_pool(
            units=available_unit_pools[component.inv_item_id]["customer"],
            required_quantity=required_quantity,
            allow_larger_splittable_unit=component.inv_item.is_splittable,
        )

        reserved_quantity = required_quantity - remaining_quantity

        if reserved_quantity < required_quantity:
            insufficient_components.append({
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
            "reservations": selected_reservations,
        })

    if insufficient_components:
        raise ValidationError({
            "customer_components": insufficient_components,
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
            }
            for row in reservation_plan
        ],
    }


def cancel_sales_order_warehouse_state(
    *,
    sales_order,
):
    transferred_exists = WarehouseProductionReservation.objects.filter(
        sales_order=sales_order,
        status=WarehouseProductionReservation.Status.TRANSFERRED,
    ).exists()

    if transferred_exists:
        raise ValidationError(
            "Неможливо скасувати SalesOrder: частина резервів вже передана у виробництво."
        )

    with transaction.atomic():
        active_reservations = list(
            WarehouseProductionReservation.objects.select_related(
                "warehouse_unit",
            ).filter(
                sales_order=sales_order,
                status=WarehouseProductionReservation.Status.ACTIVE,
            )
        )

        units_to_restore = []
        now = timezone.now()

        for reservation in active_reservations:
            unit = reservation.warehouse_unit

            if unit.status == WarehouseUnit.Status.BLOCKED:
                unit.status = WarehouseUnit.Status.ON_STOCK
                units_to_restore.append(unit)

            reservation.status = WarehouseProductionReservation.Status.CANCELLED
            reservation.cancelled_at = now

        if units_to_restore:
            WarehouseUnit.objects.bulk_update(
                units_to_restore,
                ["status"],
            )

        if active_reservations:
            WarehouseProductionReservation.objects.bulk_update(
                active_reservations,
                ["status", "cancelled_at"],
            )

    return {
        "sales_order_id": sales_order.id,
        "cancelled_reservations": len(active_reservations),
        "restored_units": len(units_to_restore),
    }


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

    item_ids = [
        component.inv_item_id
        for component in components
    ]

    available_unit_pools = _build_available_unit_pools(
        sales_order=sales_order,
        item_ids=item_ids,
    )

    reservation_plan = []
    insufficient_required_components = []

    for component in components:
        required_quantity = _to_decimal(component.quantity)
        remaining_quantity = required_quantity
        component_reservations = []

        if component.fulfillment_mode == SalesOrderComponent.FulfillmentMode.CUSTOMER:
            selected_reservations, remaining_quantity = _select_units_from_pool(
                units=available_unit_pools[component.inv_item_id]["customer"],
                required_quantity=required_quantity,
                allow_larger_splittable_unit=component.inv_item.is_splittable,
            )
            component_reservations.extend(selected_reservations)

        elif component.fulfillment_mode == SalesOrderComponent.FulfillmentMode.MIXED:
            donor_reservations, remaining_quantity = _select_units_from_pool(
                units=available_unit_pools[component.inv_item_id]["donor"],
                required_quantity=required_quantity,
                allow_larger_splittable_unit=False,
            )
            component_reservations.extend(donor_reservations)

            if remaining_quantity > ZERO:
                own_reservations, remaining_quantity = _select_units_from_pool(
                    units=available_unit_pools[component.inv_item_id]["own"],
                    required_quantity=remaining_quantity,
                    allow_larger_splittable_unit=component.inv_item.is_splittable,
                )
                component_reservations.extend(own_reservations)

        reserved_quantity = required_quantity - remaining_quantity

        if reserved_quantity < required_quantity:
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