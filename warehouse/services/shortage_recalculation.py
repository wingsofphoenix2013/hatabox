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


def recalculate_warehouse_shortages():
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

    confirmed_components = (
        SalesOrderComponent.objects.select_related(
            "sales_order",
        ).filter(
            sales_order__status=SalesOrder.Status.CONFIRMED,
            fulfillment_mode=SalesOrderComponent.FulfillmentMode.MIXED,
        )
    )

    for component in confirmed_components:
        required_quantity_by_item[component.inv_item_id] += _to_decimal(
            component.quantity
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
        WarehouseSalesOrderShortage.objects.all().delete()

        if shortages_to_create:
            WarehouseSalesOrderShortage.objects.bulk_create(
                shortages_to_create,
            )

    return {
        "shortages": len(shortages_to_create),
        "recalculated_at": now,
    }