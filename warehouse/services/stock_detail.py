from collections import defaultdict
from decimal import Decimal
from typing import Dict, List

from django.db.models import Q, Sum
from django.db.models.functions import Coalesce

from inventory.models import InvItem
from orders.models import (
    ExternalOrderItem,
    ExternalReceiptItem,
    TollingOrderItem,
    TollingReceiptItem,
)
from warehouse.models import WarehouseUnit, MovementPlanItem, MovementPlan


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
    reserved_unit_ids = set(
        MovementPlanItem.objects.filter(
            plan__status=MovementPlan.Status.ACTIVE
        ).values_list("warehouse_unit_id", flat=True)
    )

    units = [
        unit
        for unit in WarehouseUnit.objects.select_related(
            "location",
            "storage_place",
            "storage_place__location",
        ).filter(
            inventory_item_id=item_id,
            is_active=True,
        )
        if unit.id not in reserved_unit_ids
    ]

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
                "storage_place_full_display": unit.storage_place.get_display_name_verbose(),
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
                "storage_place_full_display": None,
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


def _build_reserved_stock_rows(item_id: int) -> List[dict]:
    plan_items = list(
        MovementPlanItem.objects.select_related(
            "plan",
            "warehouse_unit",
            "warehouse_unit__location",
            "warehouse_unit__storage_place",
            "warehouse_unit__storage_place__location",
        ).filter(
            warehouse_unit__inventory_item_id=item_id,
            warehouse_unit__is_active=True,
            plan__status=MovementPlan.Status.ACTIVE,
            is_reserved=True,
        )
    )

    rows = []

    for plan_item in plan_items:
        unit = plan_item.warehouse_unit

        if unit.storage_place_id is not None:
            location = unit.storage_place.location
            placement_type = "storage_place"
            storage_place_id = unit.storage_place.id
            storage_place_code = unit.storage_place.code
            storage_place_display_name = unit.storage_place.get_display_name()
            storage_place_full_display = unit.storage_place.get_display_name_verbose()
        else:
            location = unit.location
            placement_type = "location"
            storage_place_id = None
            storage_place_code = None
            storage_place_display_name = None
            storage_place_full_display = None

        plan = plan_item.plan

        if plan.target_location is not None:
            target_location = plan.target_location
            target_storage_place_id = None
            target_storage_place_code = None
            target_storage_place_display_name = None
            target_storage_place_full_display = None
        else:
            target_location = plan.target_storage_place.location
            target_storage_place_id = plan.target_storage_place.id
            target_storage_place_code = plan.target_storage_place.code
            target_storage_place_display_name = plan.target_storage_place.get_display_name()
            target_storage_place_full_display = plan.target_storage_place.get_display_name_verbose()

        rows.append({
            "placement_type": placement_type,
            "location_id": location.id,
            "location_code": location.code,
            "location_name": location.name,
            "storage_place_id": storage_place_id,
            "storage_place_code": storage_place_code,
            "storage_place_display_name": storage_place_display_name,
            "storage_place_full_display": storage_place_full_display,
            "quantity": plan_item.reserved_quantity,
            "movement_plan_id": plan.id,
            "movement_plan_status": plan.status,
            "movement_plan_planned_at": plan.planned_at,
            "target_location_id": target_location.id,
            "target_location_code": target_location.code,
            "target_location_name": target_location.name,
            "target_storage_place_id": target_storage_place_id,
            "target_storage_place_code": target_storage_place_code,
            "target_storage_place_display_name": target_storage_place_display_name,
            "target_storage_place_full_display": target_storage_place_full_display,
            "movement_plan_item_id": plan_item.id,
            "requires_split": plan_item.requires_split,
            "move_quantity": plan_item.move_quantity,
            "remainder_quantity": plan_item.remainder_quantity,
        })

    rows.sort(
        key=lambda row: (
            row["location_code"] or "",
            0 if row["placement_type"] == "location" else 1,
            row["storage_place_full_display"] or "",
            row["movement_plan_id"],
            row["movement_plan_item_id"],
        )
    )

    return rows

def _build_reserved_quantity(item_id: int) -> Decimal:
    reserved_units = WarehouseUnit.objects.filter(
        inventory_item_id=item_id,
        is_active=True,
        movement_plan_items__plan__status=MovementPlan.Status.ACTIVE,
    )

    return sum(
        (_to_decimal(unit.quantity) for unit in reserved_units),
        ZERO,
    )


def _build_pending_intake_rows(item_id: int) -> List[dict]:
    procurement_receipt_items = list(
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

    tolling_receipt_items = list(
        TollingReceiptItem.objects.select_related(
            "receipt_document",
            "receipt_document__order",
            "receipt_document__order__organization",
            "order_item",
            "order_item__order",
            "order_item__order__organization",
        ).filter(
            order_item__inv_item_id=item_id,
            receipt_document__completed=True,
            receipt_document__sent_to_warehouse=False,
        ).exclude(
            warehouse_units__is_active=True,
        )
    )

    rows = []

    for receipt_item in procurement_receipt_items:
        is_unconverted = receipt_item.order_item.requires_unit_conversion

        rows.append({
            "source_type": "procurement",
            "receipt_item_id": receipt_item.id,
            "receipt_document_id": receipt_item.receipt_document.id,
            "receipt_no": receipt_item.receipt_document.receipt_no,
            "receipt_date": receipt_item.receipt_document.receipt_date,
            "order_item_id": receipt_item.order_item.id,
            "order_id": receipt_item.order_item.order.id,
            "order_no": receipt_item.order_item.order.order_no,
            "order_created_at": receipt_item.order_item.order.created_at,
            "counterparty_id": receipt_item.order_item.order.vendor.id,
            "counterparty_name": receipt_item.order_item.order.vendor.name,
            "quantity": ZERO if is_unconverted else _to_decimal(receipt_item.received_quantity),
            "has_unconverted_quantity": is_unconverted,
        })

    for receipt_item in tolling_receipt_items:
        rows.append({
            "source_type": "tolling",
            "receipt_item_id": receipt_item.id,
            "receipt_document_id": receipt_item.receipt_document.id,
            "receipt_no": receipt_item.receipt_document.receipt_no,
            "receipt_date": receipt_item.receipt_document.receipt_date,
            "order_item_id": receipt_item.order_item.id,
            "order_id": receipt_item.order_item.order.id,
            "order_no": receipt_item.order_item.order.order_no,
            "order_created_at": receipt_item.order_item.order.created_at,
            "counterparty_id": receipt_item.order_item.order.organization.id,
            "counterparty_name": receipt_item.order_item.order.organization.name,
            "quantity": _to_decimal(receipt_item.received_quantity),
            "has_unconverted_quantity": False,
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
    procurement_completed_receipt_sums = ExternalReceiptItem.objects.filter(
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

    procurement_completed_received_by_order_item = {
        row["order_item_id"]: _to_decimal(row["completed_received_quantity"])
        for row in procurement_completed_receipt_sums
    }

    procurement_order_items = list(
        ExternalOrderItem.objects.select_related(
            "order",
            "order__vendor",
        ).filter(
            vendor_item__item_id=item_id,
            order__status="in_progress",
        )
    )

    tolling_completed_receipt_sums = TollingReceiptItem.objects.filter(
        order_item__inv_item_id=item_id,
        receipt_document__completed=True,
    ).values(
        "order_item_id",
    ).annotate(
        completed_received_quantity=Coalesce(
            Sum("received_quantity"),
            ZERO,
        )
    )

    tolling_completed_received_by_order_item = {
        row["order_item_id"]: _to_decimal(row["completed_received_quantity"])
        for row in tolling_completed_receipt_sums
    }

    tolling_order_items = list(
        TollingOrderItem.objects.select_related(
            "order",
            "order__organization",
        ).filter(
            inv_item_id=item_id,
            order__status="active",
        )
    )

    rows = []

    for order_item in procurement_order_items:
        is_unconverted = order_item.requires_unit_conversion
        completed_received = procurement_completed_received_by_order_item.get(order_item.id, ZERO)

        if is_unconverted:
            remaining = ZERO
        else:
            remaining = _to_decimal(order_item.quantity) - completed_received
            if remaining < ZERO:
                remaining = ZERO

        if remaining == ZERO and not is_unconverted:
            continue

        rows.append({
            "source_type": "procurement",
            "order_item_id": order_item.id,
            "order_id": order_item.order.id,
            "order_no": order_item.order.order_no,
            "order_created_at": order_item.order.created_at,
            "counterparty_id": order_item.order.vendor.id,
            "counterparty_name": order_item.order.vendor.name,
            "quantity": remaining,
            "has_unconverted_quantity": is_unconverted,
        })

    for order_item in tolling_order_items:
        completed_received = tolling_completed_received_by_order_item.get(order_item.id, ZERO)
        remaining = _to_decimal(order_item.quantity) - completed_received
        if remaining < ZERO:
            remaining = ZERO

        if remaining == ZERO:
            continue

        rows.append({
            "source_type": "tolling",
            "order_item_id": order_item.id,
            "order_id": order_item.order.id,
            "order_no": order_item.order.order_no,
            "order_created_at": order_item.order.created_at,
            "counterparty_id": order_item.order.organization.id,
            "counterparty_name": order_item.order.organization.name,
            "quantity": remaining,
            "has_unconverted_quantity": False,
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
    reserved_stock_rows = _build_reserved_stock_rows(item.id)
    reserved_quantity = _build_reserved_quantity(item.id)
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
            "reserved_quantity": reserved_quantity,
            "total_pending_intake_quantity": total_pending_intake_quantity,
            "total_incoming_quantity": total_incoming_quantity,
            "has_unconverted_pending_intake": has_unconverted_pending_intake,
            "has_unconverted_incoming": has_unconverted_incoming,
            "locations": locations,
        },
        "stock_rows": stock_rows,
        "reserved_stock_rows": reserved_stock_rows,
        "pending_intake_rows": pending_intake_rows,
        "incoming_rows": incoming_rows,
    }