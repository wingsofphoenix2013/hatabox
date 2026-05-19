from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum

from inventory.models import InvItem
from sales.models import SalesOrder, SalesOrderComponent
from warehouse.models import WarehouseProductionReservation

from warehouse.models import WarehouseSalesOrderShortage


ZERO = Decimal("0.000")


def build_shortage_detail(
    *,
    inv_item_id,
):
    try:
        shortage = WarehouseSalesOrderShortage.objects.select_related(
            "inv_item",
            "inv_item__unit",
        ).get(
            inv_item_id=inv_item_id,
        )
    except WarehouseSalesOrderShortage.DoesNotExist:
        inv_item = InvItem.objects.select_related(
            "unit",
        ).get(
            pk=inv_item_id,
        )

        return {
            "inv_item": inv_item.id,
            "inv_item_code": inv_item.internal_code,
            "inv_item_name": inv_item.name,
            "inventory_item_unit_symbol": inv_item.unit.symbol,

            "summary": {
                "required_quantity": ZERO,
                "available_quantity": ZERO,
                "missing_quantity": ZERO,
                "sales_orders_count": 0,
                "last_recalculated_at": None,
            },

            "rows": [],
            "allocations": [],
        }

    inv_item = shortage.inv_item

    components = list(
        SalesOrderComponent.objects.select_related(
            "sales_order",
            "sales_order__organization",
            "sales_order__product",
            "sales_order__product__product_family",
        ).filter(
            sales_order__status__in=[
                SalesOrder.Status.CONFIRMED,
                SalesOrder.Status.IN_PROGRESS,
            ],
            fulfillment_mode=SalesOrderComponent.FulfillmentMode.MIXED,
            inv_item_id=inv_item_id,
        ).order_by(
            "sales_order__created_at",
            "sales_order_id",
            "id",
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
        ] = row["total_quantity"]

    detail_rows = []

    for component in components:
        remaining_quantity = (
            component.quantity
            - reserved_quantity_by_component[component.id]
        )

        if remaining_quantity <= ZERO:
            continue

        detail_rows.append({
            "sales_order": component.sales_order.id,
            "sales_order_status": component.sales_order.status,
            "sales_order_created_at": component.sales_order.created_at,

            "organization": component.sales_order.organization.id,
            "organization_name": component.sales_order.organization.name,

            "product": component.sales_order.product.id,
            "product_code": component.sales_order.product.code,
            "product_name": component.sales_order.product.product_family.name,

            "component_id": component.id,

            "required_quantity": remaining_quantity,
        })

    sales_order_ids = {
        row["sales_order"]
        for row in detail_rows
    }

    allocations = []

    reservations = (
        WarehouseProductionReservation.objects.select_related(
            "warehouse_unit",
            "sales_order",
            "sales_order__product",
            "sales_order__product__product_family",
            "production_order_step_component",
            "production_order_step_component__production_order_step",
            "production_order_step_component__production_order_step__production_order",
        ).filter(
            warehouse_unit__inventory_item_id=inv_item_id,
            status__in=[
                WarehouseProductionReservation.Status.ACTIVE,
                WarehouseProductionReservation.Status.TRANSFERRED,
            ],
        ).order_by(
            "sales_order_id",
            "id",
        )
    )

    for reservation in reservations:
        step = reservation.production_order_step_component.production_order_step
        sales_order = reservation.sales_order

        allocations.append({
            "reservation": reservation.id,
            "reservation_status": reservation.status,

            "warehouse_unit": reservation.warehouse_unit_id,
            "warehouse_unit_status": reservation.warehouse_unit.status,

            "sales_order": sales_order.id,

            "organization": sales_order.organization_id,
            "organization_name": sales_order.organization.name,

            "serial_number": step.production_order.serial_number,

            "product": sales_order.product_id,
            "product_code": sales_order.product.code,
            "product_name": sales_order.product.product_family.name,

            "production_order": step.production_order_id,
            "production_order_step": step.id,
            "production_order_step_name": step.name,

            "quantity": reservation.quantity,
        })

    return {
        "inv_item": inv_item.id,
        "inv_item_code": inv_item.internal_code,
        "inv_item_name": inv_item.name,
        "inventory_item_unit_symbol": inv_item.unit.symbol,

        "summary": {
            "required_quantity": shortage.required_quantity,
            "available_quantity": shortage.available_quantity,
            "missing_quantity": shortage.missing_quantity,
            "sales_orders_count": len(sales_order_ids),
            "last_recalculated_at": shortage.last_recalculated_at,
        },

        "rows": detail_rows,
        "allocations": allocations,
    }