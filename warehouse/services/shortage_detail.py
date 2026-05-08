from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce

from warehouse.models import WarehouseSalesOrderShortage


ZERO = Decimal("0.000")


def _to_decimal(value) -> Decimal:
    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def build_shortage_detail(
    *,
    inv_item_id,
):
    shortage_rows = list(
        WarehouseSalesOrderShortage.objects.select_related(
            "sales_order",
            "sales_order__organization",
            "sales_order__product",
            "sales_order_component",
            "inv_item",
            "inv_item__unit",
        ).filter(
            inv_item_id=inv_item_id,
        ).order_by(
            "sales_order__created_at",
            "sales_order_id",
            "sales_order_component_id",
        )
    )

    if not shortage_rows:
        return None

    first_row = shortage_rows[0]
    inv_item = first_row.inv_item

    total_missing_quantity = sum(
        (_to_decimal(row.missing_quantity) for row in shortage_rows),
        ZERO,
    )

    customer_missing_quantity = sum(
        (
            _to_decimal(row.missing_quantity)
            for row in shortage_rows
            if row.fulfillment_mode == "customer"
        ),
        ZERO,
    )

    mixed_missing_quantity = sum(
        (
            _to_decimal(row.missing_quantity)
            for row in shortage_rows
            if row.fulfillment_mode == "mixed"
        ),
        ZERO,
    )

    sales_order_ids = {
        row.sales_order_id
        for row in shortage_rows
    }

    return {
        "inv_item": inv_item.id,
        "inv_item_code": inv_item.internal_code,
        "inv_item_name": inv_item.name,
        "inventory_item_unit_symbol": inv_item.unit.symbol,
        "is_required_for_start": first_row.is_required_for_start,

        "summary": {
            "total_missing_quantity": total_missing_quantity,
            "customer_missing_quantity": customer_missing_quantity,
            "mixed_missing_quantity": mixed_missing_quantity,
            "sales_orders_count": len(sales_order_ids),
        },

        "rows": [
            {
                "shortage_id": row.id,

                "sales_order": row.sales_order.id,
                "sales_order_status": row.sales_order.status,

                "organization": row.sales_order.organization.id,
                "organization_name": row.sales_order.organization.name,

                "product": row.sales_order.product.id,
                "product_code": row.sales_order.product.code,
                "product_name": str(row.sales_order.product),

                "component_id": row.sales_order_component.id,

                "fulfillment_mode": row.fulfillment_mode,

                "missing_quantity": row.missing_quantity,

                "last_checked_at": row.last_checked_at,
            }
            for row in shortage_rows
        ],
    }