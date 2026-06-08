from decimal import Decimal

from orders.models import (
    ExternalOrderItemWarehouseCost,
)
from warehouse.models import (
    WarehouseReceiptItemConversion,
)


VAT_RATE = Decimal("0.20")
VAT_DIVISOR = Decimal("1.20")


def recalculate_order_item_warehouse_cost(order_item):
    line_total_amount = order_item.quantity * order_item.agreed_price

    warehouse_quantity = order_item.quantity

    if order_item.requires_unit_conversion:
        warehouse_quantity = Decimal("0.000")

        conversions = WarehouseReceiptItemConversion.objects.filter(
            receipt_item__order_item=order_item,
        )

        for conversion in conversions:
            warehouse_quantity += conversion.target_quantity

        if warehouse_quantity <= 0:
            return None

    if warehouse_quantity <= 0:
        return None

    cost_with_vat_per_warehouse_unit = (
        line_total_amount / warehouse_quantity
    )

    if order_item.order.vendor.vat:
        vat_per_warehouse_unit = (
            cost_with_vat_per_warehouse_unit
            * VAT_RATE
            / VAT_DIVISOR
        )
    else:
        vat_per_warehouse_unit = Decimal("0.000000")

    cost_without_vat_per_warehouse_unit = (
        cost_with_vat_per_warehouse_unit
        - vat_per_warehouse_unit
    )

    return ExternalOrderItemWarehouseCost.objects.update_or_create(
        order=order_item.order,
        order_item=order_item,
        defaults={
            "inventory_item": order_item.vendor_item.item,
            "source_quantity": order_item.quantity,
            "warehouse_quantity": warehouse_quantity,
            "line_total_amount": line_total_amount,
            "cost_with_vat_per_warehouse_unit": cost_with_vat_per_warehouse_unit,
            "vat_per_warehouse_unit": vat_per_warehouse_unit,
            "cost_without_vat_per_warehouse_unit": cost_without_vat_per_warehouse_unit,
        },
    )