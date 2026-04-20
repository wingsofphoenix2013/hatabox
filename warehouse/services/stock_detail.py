from collections import defaultdict
from decimal import Decimal
from typing import Dict, List

from django.db.models import Q, Sum
from django.db.models.functions import Coalesce

from inventory.models import InvItem
from orders.models import ExternalOrderItem, ExternalReceiptItem
from warehouse.models import WarehouseUnit


ZERO = Decimal("0.000")


def _to_decimal(value) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _serialize_location(location) -> dict:
    return {
        "id": location.id,
        "code": location.code,
        "name": location.name,
    }


def _build_header(item: InvItem) -> dict:
    return {
        "inventory_item_id": item.id,
        "inventory_item_code": item.internal_code,
        "inventory_item_name": item.name,
        "inventory_item_category_id": item.category_id,
        "inventory_item_category_name": item.category.name,
        "inventory_item_unit_id": item.unit_id,
        "inventory_item_unit_name": item.unit.name,
        "inventory_item_unit_symbol": item.unit.symbol,
        "image": item.image.url if item.image else None,
        "qr_item": item.qr_item,
        "is_splittable": item.is_splittable,
        "requires_storage_place": item.requires_storage_place,
    }


def _build_stock_rows(item_id: int) -> List[dict]:
    units = list(
        WarehouseUnit.objects.select_related(
            "location",
            "storage_place",
            "storage_place__location",
        ).filter(
            inventory_item_id=item_id,
            is_active=True,
        )
    )

    grouped: Dict[tuple, Decimal] = defaultdict(lambda: ZERO)
    placement_meta: Dict[tuple, dict] = {}

    for unit in units:
        if unit.storage_place_id is not None:
            location = unit.storage_place.location
            key = ("storage_place", unit.storage_place_id)
            placement_meta[key] = {
                "placement_type": "storage_place",
                "location_id": location.id,
                "location_code": location.code,
                "location_name": location.name,
                "storage_place_id": unit.storage_place.id,
                "storage_place_code": unit.storage_place.code,
                "storage_place_display_name": unit.storage_place.get_display_name(),
            }
        else:
            location = unit.location
            key = ("location", location.id)
            placement_meta[key] = {
                "placement_type": "location",
                "location_id": location.id,
                "location_code": location.code,
                "location_name": location.name,
                "storage_place_id": None,
                "storage_place_code": None,
                "storage_place_display_name": None,
            }

        grouped[key] += _to_decimal(unit.quantity)

    rows = []
    for key, quantity in grouped.items():
        row = {
            **placement_meta[key],
            "quantity": quantity,
        }
        rows.append(row)

    rows.sort(
        key=lambda row: (
            row["location_code"] or "",
            0 if row["placement_type"] == "location" else 1,
            row["storage_place_display_name"] or "",
            row["location_id"] or 0,
            row["storage_place_id"] or 0,
        )
    )
    return rows


def _build_pending_intake_rows(item_id: int) -> List[dict]:
    receipt_items = list(
        ExternalReceiptItem.objects.select_related(
            "receipt_document",
            "receipt_document__order",
            "receipt_document__order__vendor",
            "order_item",
            "order_item__order",
            "order_item__order__vendor",
        ).filter(
            order_item__vendor_item__item_id=item_id,
            receipt_document__completed=True,
            receipt_document__sent_to_warehouse=False,
        ).exclude(
            warehouse_units__is_active=True,
        )
    )

    rows = []
    for receipt_item in receipt_items:
        is_unconverted = receipt_item.order_item.requires_unit_conversion

        rows.append({
            "receipt_item_id": receipt_item.id,
            "receipt_document_id": receipt_item.receipt_document.id,
            "receipt_no": receipt_item.receipt_document.receipt_no,
            "receipt_date": receipt_item.receipt_document.receipt_date,
            "order_item_id": receipt_item.order_item.id,
            "order_id": receipt_item.order_item.order.id,
            "order_no": receipt_item.order_item.order.order_no,
            "order_created_at": receipt_item.order_item.order.created_at,
            "vendor_id": receipt_item.order_item.order.vendor.id,
            "vendor_name": receipt_item.order_item.order.vendor.name,
            "quantity": ZERO if is_unconverted else _to_decimal(receipt_item.received_quantity),
            "has_unconverted_quantity": is_unconverted,
        })

    rows.sort(
        key=lambda row: (
            row["receipt_date"] or "",
            row["receipt_document_id"],
            row["receipt_item_id"],
        )
    )
    return rows


def _build_incoming_rows(item_id: int) -> List[dict]:
    completed_receipt_sums = ExternalReceiptItem.objects.filter(
        order_item__vendor_item__item_id=item_id,
        receipt_document__completed=True,
    ).values(
        "order_item_id",
    ).annotate(
        completed_received_quantity=Coalesce(
            Sum("received_quantity"),
            ZERO,
        )
    )

    completed_received_by_order_item = {
        row["order_item_id"]: _to_decimal(row["completed_received_quantity"])
        for row in completed_receipt_sums
    }

    order_items = list(
        ExternalOrderItem.objects.select_related(
            "order",
            "order__vendor",
        ).filter(
            vendor_item__item_id=item_id,
            order__status="in_progress",
        )
    )

    rows = []
    for order_item in order_items:
        is_unconverted = order_item.requires_unit_conversion
        completed_received = completed_received_by_order_item.get(order_item.id, ZERO)

        if is_unconverted:
            remaining = ZERO
        else:
            remaining = _to_decimal(order_item.quantity) - completed_received
            if remaining < ZERO:
                remaining = ZERO

        if remaining == ZERO and not is_unconverted:
            continue

        rows.append({
            "order_item_id": order_item.id,
            "order_id": order_item.order.id,
            "order_no": order_item.order.order_no,
            "order_created_at": order_item.order.created_at,
            "vendor_id": order_item.order.vendor.id,
            "vendor_name": order_item.order.vendor.name,
            "quantity": remaining,
            "has_unconverted_quantity": is_unconverted,
        })

    rows.sort(
        key=lambda row: (
            row["order_created_at"] or "",
            row["order_id"],
            row["order_item_id"],
        )
    )
    return rows


def build_stock_detail(inventory_item_id: int) -> dict:
    item = InvItem.objects.select_related(
        "category",
        "unit",
    ).get(pk=inventory_item_id)

    stock_rows = _build_stock_rows(item.id)
    pending_intake_rows = _build_pending_intake_rows(item.id)
    incoming_rows = _build_incoming_rows(item.id)

    total_available_quantity = sum(
        (row["quantity"] for row in stock_rows),
        ZERO,
    )
    total_pending_intake_quantity = sum(
        (row["quantity"] for row in pending_intake_rows),
        ZERO,
    )
    total_incoming_quantity = sum(
        (row["quantity"] for row in incoming_rows),
        ZERO,
    )

    has_unconverted_pending_intake = any(
        row["has_unconverted_quantity"] for row in pending_intake_rows
    )
    has_unconverted_incoming = any(
        row["has_unconverted_quantity"] for row in incoming_rows
    )

    locations_map = {}
    for row in stock_rows:
        location_id = row["location_id"]
        locations_map[location_id] = {
            "id": row["location_id"],
            "code": row["location_code"],
            "name": row["location_name"],
        }

    locations = sorted(
        locations_map.values(),
        key=lambda row: (row["code"], row["id"]),
    )

    return {
        "header": _build_header(item),
        "summary": {
            "total_available_quantity": total_available_quantity,
            "total_pending_intake_quantity": total_pending_intake_quantity,
            "total_incoming_quantity": total_incoming_quantity,
            "has_unconverted_pending_intake": has_unconverted_pending_intake,
            "has_unconverted_incoming": has_unconverted_incoming,
            "locations": locations,
        },
        "stock_rows": stock_rows,
        "pending_intake_rows": pending_intake_rows,
        "incoming_rows": incoming_rows,
    }