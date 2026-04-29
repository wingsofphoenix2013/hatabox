from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Optional

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


def build_stock_overview(
    *,
    search: Optional[str] = None,
    category_ids: Optional[List[int]] = None,
    location_ids: Optional[List[int]] = None,
    has_stock: Optional[bool] = None,
    has_pending_intake: Optional[bool] = None,
    has_incoming: Optional[bool] = None,
    has_unconverted_pending_intake: Optional[bool] = None,
    has_unconverted_incoming: Optional[bool] = None,
    has_any_activity: Optional[bool] = None,
) -> List[dict]:
    category_ids = [int(x) for x in (category_ids or [])]
    location_ids = [int(x) for x in (location_ids or [])]

    item_queryset = InvItem.objects.select_related(
        "category",
        "unit",
    )

    if search:
        item_queryset = item_queryset.filter(
            Q(internal_code__icontains=search)
            | Q(name__icontains=search)
            | Q(category__name__icontains=search)
        )

    if category_ids:
        item_queryset = item_queryset.filter(category_id__in=category_ids)

    items = list(item_queryset)
    if not items:
        return []

    item_ids = [item.id for item in items]

    available_units_queryset = WarehouseUnit.objects.select_related(
        "location",
        "storage_place",
        "storage_place__location",
    ).filter(
        inventory_item_id__in=item_ids,
        is_active=True,
    )

    if location_ids:
        available_units_queryset = available_units_queryset.filter(
            Q(location_id__in=location_ids)
            | Q(storage_place__location_id__in=location_ids)
        )

    reserved_unit_ids = set(
        MovementPlanItem.objects.filter(
            plan__status=MovementPlan.Status.ACTIVE
        ).values_list("warehouse_unit_id", flat=True)
    )

    available_units = [
        unit
        for unit in available_units_queryset
        if unit.id not in reserved_unit_ids
    ]

    reserved_units = [
        unit
        for unit in available_units_queryset
        if unit.id in reserved_unit_ids
    ]

    available_by_item: Dict[int, Decimal] = defaultdict(lambda: ZERO)
    reserved_by_item: Dict[int, Decimal] = defaultdict(lambda: ZERO)
    locations_by_item: Dict[int, dict] = defaultdict(dict)
    available_placements_by_item: Dict[int, dict] = defaultdict(dict)

    for unit in available_units:
        available_by_item[unit.inventory_item_id] += _to_decimal(unit.quantity)

        location = unit.location
        storage_place = unit.storage_place

        if location is None and storage_place is not None:
            location = storage_place.location

        if location is not None:
            locations_by_item[unit.inventory_item_id][location.id] = _serialize_location(location)

        key = (
            location.id,
            storage_place.id if storage_place is not None else None,
        )

        if key not in available_placements_by_item[unit.inventory_item_id]:
            available_placements_by_item[unit.inventory_item_id][key] = {
                "location_code": location.code,
                "location_name": location.name,
                "storage_place_display_name": (
                    storage_place.get_display_name()
                    if storage_place is not None
                    else None
                ),
                "storage_place_full_display": (
                    storage_place.get_display_name_verbose()
                    if storage_place is not None
                    else None
                ),
                "available_quantity": ZERO,
                "unit_symbol": unit.inventory_item.unit.symbol,
            }

        available_placements_by_item[unit.inventory_item_id][key]["available_quantity"] += _to_decimal(unit.quantity)

    for unit in reserved_units:
        reserved_by_item[unit.inventory_item_id] += _to_decimal(unit.quantity)

    procurement_pending_receipts_queryset = ExternalReceiptItem.objects.select_related(
        "receipt_document",
        "order_item",
        "order_item__vendor_item",
        "order_item__vendor_item__item",
    ).filter(
        order_item__vendor_item__item_id__in=item_ids,
        receipt_document__completed=True,
        receipt_document__sent_to_warehouse=False,
        order_item__requires_unit_conversion=False,
    ).exclude(
        warehouse_units__is_active=True,
    )

    tolling_pending_receipts_queryset = TollingReceiptItem.objects.select_related(
        "receipt_document",
        "order_item",
        "order_item__inv_item",
    ).filter(
        order_item__inv_item_id__in=item_ids,
        receipt_document__completed=True,
        receipt_document__sent_to_warehouse=False,
    ).exclude(
        warehouse_units__is_active=True,
    )

    procurement_pending_receipts = list(procurement_pending_receipts_queryset)
    tolling_pending_receipts = list(tolling_pending_receipts_queryset)

    procurement_pending_intake_by_item: Dict[int, Decimal] = defaultdict(lambda: ZERO)
    tolling_pending_intake_by_item: Dict[int, Decimal] = defaultdict(lambda: ZERO)
    pending_intake_by_item: Dict[int, Decimal] = defaultdict(lambda: ZERO)

    for receipt_item in procurement_pending_receipts:
        item_id = receipt_item.order_item.vendor_item.item_id
        quantity = _to_decimal(receipt_item.received_quantity)

        procurement_pending_intake_by_item[item_id] += quantity
        pending_intake_by_item[item_id] += quantity

    for receipt_item in tolling_pending_receipts:
        item_id = receipt_item.order_item.inv_item_id
        quantity = _to_decimal(receipt_item.received_quantity)

        tolling_pending_intake_by_item[item_id] += quantity
        pending_intake_by_item[item_id] += quantity

    procurement_completed_receipt_sums = ExternalReceiptItem.objects.filter(
        order_item__vendor_item__item_id__in=item_ids,
        receipt_document__completed=True,
        order_item__requires_unit_conversion=False,
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

    procurement_incoming_order_items_queryset = ExternalOrderItem.objects.select_related(
        "order",
        "vendor_item",
        "vendor_item__item",
    ).filter(
        vendor_item__item_id__in=item_ids,
        order__status="in_progress",
        requires_unit_conversion=False,
    )

    tolling_completed_receipt_sums = TollingReceiptItem.objects.filter(
        order_item__inv_item_id__in=item_ids,
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

    tolling_incoming_order_items_queryset = TollingOrderItem.objects.select_related(
        "order",
        "inv_item",
    ).filter(
        inv_item_id__in=item_ids,
        order__status="active",
    )

    procurement_incoming_order_items = list(procurement_incoming_order_items_queryset)
    tolling_incoming_order_items = list(tolling_incoming_order_items_queryset)

    incoming_by_item: Dict[int, Decimal] = defaultdict(lambda: ZERO)

    for order_item in procurement_incoming_order_items:
        completed_received = procurement_completed_received_by_order_item.get(order_item.id, ZERO)
        remaining = _to_decimal(order_item.quantity) - completed_received
        if remaining < ZERO:
            remaining = ZERO

        incoming_by_item[order_item.vendor_item.item_id] += remaining

    for order_item in tolling_incoming_order_items:
        completed_received = tolling_completed_received_by_order_item.get(order_item.id, ZERO)
        remaining = _to_decimal(order_item.quantity) - completed_received
        if remaining < ZERO:
            remaining = ZERO

        incoming_by_item[order_item.inv_item_id] += remaining

    unconverted_pending_intake_item_ids = set(
        ExternalReceiptItem.objects.filter(
            order_item__vendor_item__item_id__in=item_ids,
            receipt_document__completed=True,
            receipt_document__sent_to_warehouse=False,
            order_item__requires_unit_conversion=True,
        ).exclude(
            warehouse_units__is_active=True,
        ).values_list("order_item__vendor_item__item_id", flat=True)
    )

    unconverted_incoming_item_ids = set(
        ExternalOrderItem.objects.filter(
            vendor_item__item_id__in=item_ids,
            requires_unit_conversion=True,
            order__status="in_progress",
        ).values_list("vendor_item__item_id", flat=True)
    )

    results = []
    for item in items:
        available_quantity = available_by_item[item.id]
        reserved_quantity = reserved_by_item[item.id]
        procurement_pending_intake_quantity = procurement_pending_intake_by_item[item.id]
        tolling_pending_intake_quantity = tolling_pending_intake_by_item[item.id]
        pending_intake_quantity = pending_intake_by_item[item.id]
        incoming_quantity = incoming_by_item[item.id]
        item_locations = sorted(
            locations_by_item[item.id].values(),
            key=lambda x: (x["code"], x["id"]),
        )
        available_placements = sorted(
            available_placements_by_item[item.id].values(),
            key=lambda x: (
                x["location_code"] or "",
                x["storage_place_full_display"] or "",
            ),
        )

        row_has_procurement_pending_intake = procurement_pending_intake_quantity > ZERO
        row_has_tolling_pending_intake = tolling_pending_intake_quantity > ZERO
        row_has_unconverted_pending_intake = item.id in unconverted_pending_intake_item_ids
        row_has_unconverted_incoming = item.id in unconverted_incoming_item_ids

        row_matches_pending_intake = (
            pending_intake_quantity > ZERO
            or row_has_unconverted_pending_intake
        )
        row_matches_incoming = (
            incoming_quantity > ZERO
            or row_has_unconverted_incoming
        )

        row_has_any_activity = (
            available_quantity > ZERO
            or row_matches_pending_intake
            or row_matches_incoming
        )

        row = {
            "inventory_item_id": item.id,
            "inventory_item_code": item.internal_code,
            "inventory_item_name": item.name,
            "inventory_item_category_id": item.category_id,
            "inventory_item_category_name": item.category.name,
            "inventory_item_unit_name": item.unit.name,
            "inventory_item_unit_symbol": item.unit.symbol,
            "available_quantity": available_quantity,
            "reserved_quantity": reserved_quantity,
            "pending_intake_quantity": pending_intake_quantity,
            "procurement_pending_intake_quantity": procurement_pending_intake_quantity,
            "tolling_pending_intake_quantity": tolling_pending_intake_quantity,
            "incoming_quantity": incoming_quantity,
            "has_procurement_pending_intake": row_has_procurement_pending_intake,
            "has_tolling_pending_intake": row_has_tolling_pending_intake,
            "has_unconverted_pending_intake": row_has_unconverted_pending_intake,
            "has_unconverted_incoming": row_has_unconverted_incoming,
            "locations": item_locations,
            "available_placements": available_placements,
        }
        
        if has_stock is not None and (available_quantity > ZERO) != has_stock:
            continue

        if has_pending_intake is not None and row_matches_pending_intake != has_pending_intake:
            continue

        if has_incoming is not None and row_matches_incoming != has_incoming:
            continue

        if (
            has_unconverted_pending_intake is not None
            and row_has_unconverted_pending_intake != has_unconverted_pending_intake
        ):
            continue

        if (
            has_unconverted_incoming is not None
            and row_has_unconverted_incoming != has_unconverted_incoming
        ):
            continue

        if location_ids and not item_locations:
            continue

        if has_any_activity is not None and row_has_any_activity != has_any_activity:
            continue

        results.append(row)

    results.sort(
        key=lambda row: (
            row["inventory_item_category_name"],
            row["inventory_item_name"],
            row["inventory_item_id"],
        )
    )
    return results