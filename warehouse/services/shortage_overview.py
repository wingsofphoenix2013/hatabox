from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from orders.models import (
    ExternalOrderItem,
    ExternalReceiptItem,
    TollingOrderItem,
    TollingReceiptItem,
)
from sales.models import SalesOrderComponent

from warehouse.models import WarehouseSalesOrderShortage


ZERO = Decimal("0.000")


def _to_decimal(value) -> Decimal:
    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def build_shortage_overview():
    shortage_rows = list(
        WarehouseSalesOrderShortage.objects.select_related(
            "inv_item",
            "inv_item__unit",
        ).values(
            "inv_item_id",
            "inv_item__internal_code",
            "inv_item__name",
            "inv_item__unit__symbol",
            "fulfillment_mode",
            "is_required_for_start",
        ).annotate(
            missing_quantity=Coalesce(
                Sum("missing_quantity"),
                ZERO,
            ),
            sales_orders_count=Count(
                "sales_order",
                distinct=True,
            ),
            components_count=Count(
                "sales_order_component",
                distinct=True,
            ),
        ).order_by(
            "inv_item__name",
            "fulfillment_mode",
            "-is_required_for_start",
        )
    )

    mixed_item_ids = {
        row["inv_item_id"]
        for row in shortage_rows
        if row["fulfillment_mode"] == SalesOrderComponent.FulfillmentMode.MIXED
    }

    procurement_pending_by_item = {}
    procurement_incoming_by_item = {}
    has_unconverted_incoming_by_item = {}

    if mixed_item_ids:
        pending_rows = (
            ExternalReceiptItem.objects.filter(
                order_item__vendor_item__item_id__in=mixed_item_ids,
                receipt_document__completed=True,
                receipt_document__sent_to_warehouse=False,
                order_item__requires_unit_conversion=False,
                warehouse_units__isnull=True,
            ).values(
                "order_item__vendor_item__item_id",
            ).annotate(
                total=Coalesce(
                    Sum("received_quantity"),
                    ZERO,
                )
            )
        )

        procurement_pending_by_item = {
            row["order_item__vendor_item__item_id"]: _to_decimal(row["total"])
            for row in pending_rows
        }

        completed_receipt_rows = (
            ExternalReceiptItem.objects.filter(
                order_item__vendor_item__item_id__in=mixed_item_ids,
                receipt_document__completed=True,
            ).values(
                "order_item_id",
            ).annotate(
                completed_received_quantity=Coalesce(
                    Sum("received_quantity"),
                    ZERO,
                )
            )
        )

        completed_received_by_order_item = {
            row["order_item_id"]: _to_decimal(row["completed_received_quantity"])
            for row in completed_receipt_rows
        }

        incoming_rows = ExternalOrderItem.objects.select_related(
            "vendor_item",
        ).filter(
            vendor_item__item_id__in=mixed_item_ids,
            order__status="in_progress",
            requires_unit_conversion=False,
        )

        for order_item in incoming_rows:
            completed_received = completed_received_by_order_item.get(
                order_item.id,
                ZERO,
            )

            remaining = _to_decimal(order_item.quantity) - completed_received

            if remaining <= ZERO:
                continue

            item_id = order_item.vendor_item.item_id

            procurement_incoming_by_item.setdefault(item_id, ZERO)
            procurement_incoming_by_item[item_id] += remaining

        unconverted_rows = ExternalOrderItem.objects.filter(
            vendor_item__item_id__in=mixed_item_ids,
            order__status="in_progress",
            requires_unit_conversion=True,
        ).values_list(
            "vendor_item__item_id",
            flat=True,
        )

        has_unconverted_incoming_by_item = {
            item_id: True
            for item_id in unconverted_rows
        }

    result = []

    for row in shortage_rows:
        fulfillment_mode = row["fulfillment_mode"]
        item_id = row["inv_item_id"]

        forecast_quantity = ZERO
        has_unconverted_incoming = False
        net_missing_quantity = row["missing_quantity"]

        if fulfillment_mode == SalesOrderComponent.FulfillmentMode.MIXED:
            forecast_quantity = (
                procurement_pending_by_item.get(item_id, ZERO)
                + procurement_incoming_by_item.get(item_id, ZERO)
            )

            has_unconverted_incoming = has_unconverted_incoming_by_item.get(
                item_id,
                False,
            )

            net_missing_quantity = (
                _to_decimal(row["missing_quantity"])
                - forecast_quantity
            )

            if net_missing_quantity < ZERO:
                net_missing_quantity = ZERO

        result.append({
            "inv_item": item_id,
            "inv_item_code": row["inv_item__internal_code"],
            "inv_item_name": row["inv_item__name"],
            "inventory_item_unit_symbol": row["inv_item__unit__symbol"],
            "fulfillment_mode": fulfillment_mode,
            "is_required_for_start": row["is_required_for_start"],
            "missing_quantity": row["missing_quantity"],
            "forecast_quantity": forecast_quantity,
            "has_unconverted_incoming": has_unconverted_incoming,
            "net_missing_quantity": net_missing_quantity,
            "sales_orders_count": row["sales_orders_count"],
            "components_count": row["components_count"],
            "blocks_confirmation": row["is_required_for_start"],
        })

    return result