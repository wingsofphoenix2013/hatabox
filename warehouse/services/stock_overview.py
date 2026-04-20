from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Optional

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


def build_stock_overview(
    *,
    search: Optional[str] = None,
    category_ids: Optional[List[int]] = None,
    location_ids: Optional[List[int]] = None,
    has_stock: Optional[bool] = None,
    has_pending_intake: Optional[bool] = None,
    has_incoming: Optional[bool] = None,
    has_unconverted_expectation: Optional[bool] = None,
) -> List[dict]:
    print("stock_overview: start")

    category_ids = [int(x) for x in (category_ids or [])]
    location_ids = [int(x) for x in (location_ids or [])]

    print("stock_overview: filters", {
        "search": search,
        "category_ids": category_ids,
        "location_ids": location_ids,
        "has_stock": has_stock,
        "has_pending_intake": has_pending_intake,
        "has_incoming": has_incoming,
        "has_unconverted_expectation": has_unconverted_expectation,
    })

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
    print("stock_overview: items loaded", len(items))

    if not items:
        print("stock_overview: no items, return []")
        return []

    item_ids = [item.id for item in items]
    print("stock_overview: item_ids built", len(item_ids))

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

    available_units = list(available_units_queryset)
    print("stock_overview: available_units loaded", len(available_units))

    available_by_item: Dict[int, Decimal] = defaultdict(lambda: ZERO)
    locations_by_item: Dict[int, dict] = defaultdict(dict)

    for unit in available_units:
        print("stock_overview: available unit", unit.id, unit.inventory_item_id)

        available_by_item[unit.inventory_item_id] += _to_decimal(unit.quantity)

        location = unit.location
        if location is None and unit.storage_place_id is not None:
            print("stock_overview: resolving storage_place location", unit.id, unit.storage_place_id)
            location = unit.storage_place.location

        if location is not None:
            locations_by_item[unit.inventory_item_id][location.id] = _serialize_location(location)

    print("stock_overview: available aggregates built", len(available_by_item))

    pending_receipts_queryset = ExternalReceiptItem.objects.select_related(
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

    pending_receipts = list(pending_receipts_queryset)
    print("stock_overview: pending_receipts loaded", len(pending_receipts))

    pending_intake_by_item: Dict[int, Decimal] = defaultdict(lambda: ZERO)
    for receipt_item in pending_receipts:
        print("stock_overview: pending receipt item", receipt_item.id)
        item_id = receipt_item.order_item.vendor_item.item_id
        pending_intake_by_item[item_id] += _to_decimal(receipt_item.received_quantity)

    print("stock_overview: pending aggregates built", len(pending_intake_by_item))

    completed_receipt_sums = ExternalReceiptItem.objects.filter(
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

    completed_received_by_order_item = {
        row["order_item_id"]: _to_decimal(row["completed_received_quantity"])
        for row in completed_receipt_sums
    }
    print(
        "stock_overview: completed_received_by_order_item built",
        len(completed_received_by_order_item),
    )

    incoming_order_items_queryset = ExternalOrderItem.objects.select_related(
        "order",
        "vendor_item",
        "vendor_item__item",
    ).filter(
        vendor_item__item_id__in=item_ids,
        order__status="in_progress",
        requires_unit_conversion=False,
    )

    incoming_order_items = list(incoming_order_items_queryset)
    print("stock_overview: incoming_order_items loaded", len(incoming_order_items))

    incoming_by_item: Dict[int, Decimal] = defaultdict(lambda: ZERO)
    for order_item in incoming_order_items:
        print("stock_overview: incoming order_item", order_item.id)
        completed_received = completed_received_by_order_item.get(order_item.id, ZERO)
        remaining = _to_decimal(order_item.quantity) - completed_received
        if remaining < ZERO:
            remaining = ZERO

        incoming_by_item[order_item.vendor_item.item_id] += remaining

    print("stock_overview: incoming aggregates built", len(incoming_by_item))

    unconverted_order_item_exists = set(
        ExternalOrderItem.objects.filter(
            vendor_item__item_id__in=item_ids,
            requires_unit_conversion=True,
            order__status="in_progress",
        ).values_list("vendor_item__item_id", flat=True)
    )
    print("stock_overview: unconverted_order_item_exists built", len(unconverted_order_item_exists))

    unconverted_receipt_item_exists = set(
        ExternalReceiptItem.objects.filter(
            order_item__vendor_item__item_id__in=item_ids,
            receipt_document__completed=True,
            order_item__requires_unit_conversion=True,
        ).exclude(
            warehouse_units__is_active=True,
        ).values_list("order_item__vendor_item__item_id", flat=True)
    )
    print("stock_overview: unconverted_receipt_item_exists built", len(unconverted_receipt_item_exists))

    unconverted_item_ids = unconverted_order_item_exists | unconverted_receipt_item_exists
    print("stock_overview: unconverted_item_ids built", len(unconverted_item_ids))

    results = []
    print("stock_overview: building rows")

    for item in items:
        print("stock_overview: row", item.id, item.internal_code, item.name)

        available_quantity = available_by_item[item.id]
        pending_intake_quantity = pending_intake_by_item[item.id]
        incoming_quantity = incoming_by_item[item.id]
        has_unconverted = item.id in unconverted_item_ids

        locations = sorted(
            locations_by_item[item.id].values(),
            key=lambda x: (x["code"], x["id"]),
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
            "pending_intake_quantity": pending_intake_quantity,
            "incoming_quantity": incoming_quantity,
            "has_unconverted_expectation": has_unconverted,
            "locations": locations,
        }

        if has_stock is not None and (available_quantity > ZERO) != has_stock:
            continue

        if has_pending_intake is not None and (pending_intake_quantity > ZERO) != has_pending_intake:
            continue

        if has_incoming is not None and (incoming_quantity > ZERO) != has_incoming:
            continue

        if has_unconverted_expectation is not None and has_unconverted != has_unconverted_expectation:
            continue

        if location_ids and not locations:
            continue

        results.append(row)

    print("stock_overview: rows built", len(results))

    results.sort(
        key=lambda row: (
            row["inventory_item_category_name"],
            row["inventory_item_name"],
            row["inventory_item_id"],
        )
    )

    print("stock_overview: done")
    return results