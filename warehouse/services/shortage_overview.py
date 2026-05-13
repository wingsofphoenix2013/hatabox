from decimal import Decimal

from django.db.models import Q, Sum
from django.db.models.functions import Coalesce

from organizations.models import Organization
from orders.models import (
    ExternalOrderItem,
    ExternalReceiptItem,
    TollingOrderItem,
    TollingReceiptItem,
)

from warehouse.models import WarehouseSalesOrderShortage


ZERO = Decimal("0.000")


def _to_decimal(value) -> Decimal:
    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def build_shortage_overview(
    *,
    search=None,
):
    shortage_queryset = WarehouseSalesOrderShortage.objects.select_related(
        "inv_item",
        "inv_item__unit",
    )

    if search:
        shortage_queryset = shortage_queryset.filter(
            Q(inv_item__name__icontains=search)
            | Q(inv_item__internal_code__icontains=search)
        )

    shortage_rows = list(
        shortage_queryset.order_by(
            "inv_item__name",
            "inv_item_id",
        )
    )

    item_ids = [
        row.inv_item_id
        for row in shortage_rows
    ]

    procurement_pending_by_item = {}
    procurement_incoming_by_item = {}
    procurement_unconverted_by_item = {}

    tolling_pending_by_item = {}
    tolling_incoming_by_item = {}
    tolling_unconverted_by_item = {}

    if item_ids:
        pending_rows = (
            ExternalReceiptItem.objects.filter(
                order_item__vendor_item__item_id__in=item_ids,
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
                order_item__vendor_item__item_id__in=item_ids,
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
            vendor_item__item_id__in=item_ids,
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
            vendor_item__item_id__in=item_ids,
            order__status="in_progress",
            requires_unit_conversion=True,
        ).values_list(
            "vendor_item__item_id",
            flat=True,
        )

        procurement_unconverted_by_item = {
            item_id: True
            for item_id in unconverted_rows
        }

        tolling_pending_rows = (
            TollingReceiptItem.objects.filter(
                order_item__inv_item_id__in=item_ids,
                receipt_document__completed=True,
                receipt_document__sent_to_warehouse=False,
                order_item__requires_unit_conversion=False,
                receipt_document__order__organization__type=Organization.Type.CHARITY,
                warehouse_units__isnull=True,
            ).values(
                "order_item__inv_item_id",
            ).annotate(
                total=Coalesce(
                    Sum("received_quantity"),
                    ZERO,
                )
            )
        )

        tolling_pending_by_item = {
            row["order_item__inv_item_id"]: _to_decimal(row["total"])
            for row in tolling_pending_rows
        }

        tolling_completed_receipt_rows = (
            TollingReceiptItem.objects.filter(
                order_item__inv_item_id__in=item_ids,
                receipt_document__completed=True,
                receipt_document__order__organization__type=Organization.Type.CHARITY,
            ).values(
                "order_item_id",
            ).annotate(
                completed_received_quantity=Coalesce(
                    Sum("received_quantity"),
                    ZERO,
                )
            )
        )

        tolling_completed_received_by_order_item = {
            row["order_item_id"]: _to_decimal(row["completed_received_quantity"])
            for row in tolling_completed_receipt_rows
        }

        tolling_incoming_rows = TollingOrderItem.objects.select_related(
            "order",
        ).filter(
            inv_item_id__in=item_ids,
            order__status="active",
            order__organization__type=Organization.Type.CHARITY,
            requires_unit_conversion=False,
        )

        for order_item in tolling_incoming_rows:
            completed_received = tolling_completed_received_by_order_item.get(
                order_item.id,
                ZERO,
            )

            remaining = _to_decimal(order_item.quantity) - completed_received

            if remaining <= ZERO:
                continue

            tolling_incoming_by_item.setdefault(order_item.inv_item_id, ZERO)
            tolling_incoming_by_item[order_item.inv_item_id] += remaining

        tolling_unconverted_rows = TollingOrderItem.objects.filter(
            inv_item_id__in=item_ids,
            order__status="active",
            order__organization__type=Organization.Type.CHARITY,
            requires_unit_conversion=True,
        ).values_list(
            "inv_item_id",
            flat=True,
        )

        tolling_unconverted_by_item = {
            item_id: True
            for item_id in tolling_unconverted_rows
        }

    result = []

    for row in shortage_rows:
        item_id = row.inv_item_id

        forecast_quantity = (
            procurement_pending_by_item.get(item_id, ZERO)
            + procurement_incoming_by_item.get(item_id, ZERO)
            + tolling_pending_by_item.get(item_id, ZERO)
            + tolling_incoming_by_item.get(item_id, ZERO)
        )

        has_unconverted_incoming = (
            procurement_unconverted_by_item.get(item_id, False)
            or tolling_unconverted_by_item.get(item_id, False)
        )

        result.append({
            "inv_item": row.inv_item_id,
            "inv_item_code": row.inv_item.internal_code,
            "inv_item_name": row.inv_item.name,
            "inventory_item_unit_symbol": row.inv_item.unit.symbol,
            "required_quantity": row.required_quantity,
            "available_quantity": row.available_quantity,
            "missing_quantity": row.missing_quantity,
            "forecast_quantity": forecast_quantity,
            "has_unconverted_incoming": has_unconverted_incoming,
            "last_recalculated_at": row.last_recalculated_at,
        })

    return result