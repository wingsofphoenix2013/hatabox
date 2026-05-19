from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from organizations.models import Organization
from sales.models import SalesOrder, SalesOrderComponent

from warehouse.models import (
    MovementPlan,
    MovementPlanItem,
    WarehouseProductionReservation,
    WarehouseSalesOrderShortage,
    WarehouseUnit,
)


ZERO = Decimal("0.000")


def _to_decimal(value) -> Decimal:
    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def recalculate_warehouse_shortages(
    *,
    inv_item_ids,
):
    reserved_movement_unit_ids = set(
        MovementPlanItem.objects.filter(
            plan__status=MovementPlan.Status.ACTIVE,
            is_reserved=True,
        ).values_list("warehouse_unit_id", flat=True)
    )

    available_units = WarehouseUnit.objects.select_related(
        "tolling_source_order_item",
        "tolling_source_order_item__order",
    ).filter(
        status=WarehouseUnit.Status.ON_STOCK,
        inventory_item_id__in=inv_item_ids,
    ).exclude(
        id__in=reserved_movement_unit_ids,
    ).exclude(
        production_reservations__status=WarehouseProductionReservation.Status.ACTIVE,
    )

    available_quantity_by_item = defaultdict(lambda: ZERO)

    for unit in available_units:
        if unit.source_order_item_id:
            available_quantity_by_item[unit.inventory_item_id] += _to_decimal(
                unit.quantity
            )
            continue

        if (
            unit.tolling_source_order_item_id
            and unit.tolling_source_order_item.order.organization.type == Organization.Type.CHARITY
        ):
            available_quantity_by_item[unit.inventory_item_id] += _to_decimal(
                unit.quantity
            )

    required_quantity_by_item = defaultdict(lambda: ZERO)

    components = list(
        SalesOrderComponent.objects.select_related(
            "sales_order",
        ).filter(
            sales_order__status__in=[
                SalesOrder.Status.CONFIRMED,
                SalesOrder.Status.IN_PROGRESS,
            ],
            fulfillment_mode=SalesOrderComponent.FulfillmentMode.MIXED,
            inv_item_id__in=inv_item_ids,
        )
    )

    component_ids = [
        component.id
        for component in components
    ]

    reserved_quantity_by_component = defaultdict(lambda: ZERO)

    reservation_rows = (
        WarehouseProductionReservation.objects.filter(
            sales_order_component_id__in=component_ids,
            status__in=[
                WarehouseProductionReservation.Status.ACTIVE,
                WarehouseProductionReservation.Status.TRANSFERRED,
            ],
        ).values(
            "sales_order_component_id",
        ).annotate(
            total_quantity=Sum("quantity"),
        )
    )

    for row in reservation_rows:
        reserved_quantity_by_component[
            row["sales_order_component_id"]
        ] = _to_decimal(row["total_quantity"])

    for component in components:
        remaining_quantity = (
            _to_decimal(component.quantity)
            - reserved_quantity_by_component[component.id]
        )

        if remaining_quantity <= ZERO:
            continue

        required_quantity_by_item[component.inv_item_id] += (
            remaining_quantity
        )

    now = timezone.now()

    shortages_to_create = []

    for inv_item_id, required_quantity in required_quantity_by_item.items():
        available_quantity = available_quantity_by_item[inv_item_id]

        missing_quantity = required_quantity - available_quantity

        if missing_quantity <= ZERO:
            continue

        shortages_to_create.append(
            WarehouseSalesOrderShortage(
                inv_item_id=inv_item_id,
                required_quantity=required_quantity,
                available_quantity=available_quantity,
                missing_quantity=missing_quantity,
                last_recalculated_at=now,
            )
        )

    with transaction.atomic():
        WarehouseSalesOrderShortage.objects.filter(
            inv_item_id__in=inv_item_ids,
        ).delete()

        if shortages_to_create:
            WarehouseSalesOrderShortage.objects.bulk_create(
                shortages_to_create,
            )

    return {
        "shortages": len(shortages_to_create),
        "recalculated_at": now,
    }