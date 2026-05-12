from collections import defaultdict
from decimal import Decimal

from django.db.models import Q
from rest_framework.exceptions import ValidationError

from organizations.models import Organization
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


def _limited_quantity(available: Decimal, required: Decimal) -> Decimal:
    if available >= required:
        return required
    return available


def build_sales_order_availability(sales_order_id: int) -> dict:
    try:
        sales_order = SalesOrder.objects.select_related(
            "organization",
        ).prefetch_related(
            "components",
            "components__inv_item",
        ).get(pk=sales_order_id)
    except SalesOrder.DoesNotExist as exc:
        raise ValidationError("SalesOrder не знайдено.") from exc

    components = list(sales_order.components.select_related("inv_item").all())
    item_ids = [component.inv_item_id for component in components]

    reserved_unit_ids = set(
        MovementPlanItem.objects.filter(
            plan__status=MovementPlan.Status.ACTIVE,
            is_reserved=True,
        ).values_list("warehouse_unit_id", flat=True)
    )

    units = list(
        WarehouseUnit.objects.select_related(
            "inventory_item",
            "tolling_source_order_item",
            "tolling_source_order_item__order",
        ).filter(
            inventory_item_id__in=item_ids,
            status=WarehouseUnit.Status.ON_STOCK,
        ).exclude(
            id__in=reserved_unit_ids,
        ).exclude(
            production_reservations__status=WarehouseProductionReservation.Status.ACTIVE,
        ).order_by(
            "created_at",
            "id",
        )
    )

    customer_quantities = defaultdict(lambda: ZERO)
    donor_quantities = defaultdict(lambda: ZERO)
    own_quantities = defaultdict(lambda: ZERO)

    for unit in units:
        quantity = _to_decimal(unit.quantity)

        if unit.tolling_source_order_item_id:
            organization = unit.tolling_source_order_item.order.organization

            if organization.id == sales_order.organization_id:
                customer_quantities[unit.inventory_item_id] += quantity
            elif organization.type == Organization.Type.CHARITY:
                donor_quantities[unit.inventory_item_id] += quantity

            continue

        if unit.source_order_item_id:
            own_quantities[unit.inventory_item_id] += quantity

    component_rows = []

    can_confirm = True

    for component in components:
        required_quantity = _to_decimal(component.quantity)

        customer_available_quantity = ZERO
        donor_available_quantity = ZERO
        own_available_quantity = ZERO

        if component.fulfillment_mode == SalesOrderComponent.FulfillmentMode.CUSTOMER:
            customer_available_quantity = _limited_quantity(
                customer_quantities[component.inv_item_id],
                required_quantity,
            )
            total_available_quantity = customer_available_quantity

        elif component.fulfillment_mode == SalesOrderComponent.FulfillmentMode.MIXED:
            donor_available_quantity = _limited_quantity(
                donor_quantities[component.inv_item_id],
                required_quantity,
            )

            remaining_quantity = required_quantity - donor_available_quantity

            own_available_quantity = _limited_quantity(
                own_quantities[component.inv_item_id],
                remaining_quantity,
            )
            total_available_quantity = donor_available_quantity + own_available_quantity

        else:
            total_available_quantity = ZERO

        missing_quantity = required_quantity - total_available_quantity
        if missing_quantity < ZERO:
            missing_quantity = ZERO

        can_cover = missing_quantity == ZERO


        component_rows.append({
            "component_id": component.id,
            "inv_item": component.inv_item_id,
            "inv_item_code": component.inv_item.internal_code,
            "inv_item_name": component.inv_item.name,
            "required_quantity": required_quantity,
            "fulfillment_mode": component.fulfillment_mode,
            "customer_available_quantity": customer_available_quantity,
            "donor_available_quantity": donor_available_quantity,
            "own_available_quantity": own_available_quantity,
            "total_available_quantity": total_available_quantity,
            "missing_quantity": missing_quantity,
            "can_cover": can_cover,
        })

    return {
        "sales_order": sales_order.id,
        "can_confirm": can_confirm,
        "components": component_rows,
    }