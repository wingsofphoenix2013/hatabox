from decimal import Decimal

from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML


ZERO = Decimal("0.000")


def _to_decimal(value) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _build_source_lines(plan):
    source_lines = {}

    items = plan.items.select_related(
        "warehouse_unit",
        "warehouse_unit__inventory_item",
        "warehouse_unit__inventory_item__unit",
        "warehouse_unit__location",
        "warehouse_unit__storage_place",
        "warehouse_unit__storage_place__location",
    ).all()

    for item in items:
        unit = item.warehouse_unit
        inventory_item = unit.inventory_item
        quantity = item.move_quantity if item.requires_split else item.reserved_quantity

        if unit.storage_place is not None:
            source_location = unit.storage_place.location
            source_storage_place_id = unit.storage_place_id
            source_storage_place_full_display = unit.storage_place.get_display_name_verbose()
        else:
            source_location = unit.location
            source_storage_place_id = None
            source_storage_place_full_display = None

        key = (
            inventory_item.id,
            source_location.id,
            source_storage_place_id,
        )

        if key not in source_lines:
            source_lines[key] = {
                "inventory_item_id": inventory_item.id,
                "inventory_item_name": inventory_item.name,
                "source_location_code": source_location.code,
                "source_location_name": source_location.name,
                "source_storage_place_full_display": source_storage_place_full_display,
                "quantity": ZERO,
                "unit_symbol": inventory_item.unit.symbol,
                "has_split": False,
            }

        source_lines[key]["quantity"] += _to_decimal(quantity)
        source_lines[key]["has_split"] = (
            source_lines[key]["has_split"] or item.requires_split
        )

    rows = list(source_lines.values())
    rows.sort(
        key=lambda row: (
            row["inventory_item_name"],
            row["source_location_code"],
            row["source_storage_place_full_display"] or "",
        )
    )

    return rows


def generate_movement_plan_invoice_pdf(plan) -> bytes:
    if plan.target_storage_place is not None:
        target_location = plan.target_storage_place.location
        target_storage_place_full_display = plan.target_storage_place.get_display_name_verbose()
    else:
        target_location = plan.target_location
        target_storage_place_full_display = None

    html = render_to_string(
        "warehouse/movement_plan_invoice.html",
        {
            "plan_id": plan.id,
            "invoice_generated_at": timezone.localtime(timezone.now()),
            "planned_at": (
                timezone.localtime(plan.planned_at)
                if plan.planned_at
                else None
            ),
            "target_location_code": target_location.code,
            "target_location_name": target_location.name,
            "target_storage_place_full_display": target_storage_place_full_display,
            "rows": _build_source_lines(plan),
        },
    )

    pdf = HTML(string=html).write_pdf()
    return pdf