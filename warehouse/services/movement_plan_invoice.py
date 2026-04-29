import hashlib
import json
from decimal import Decimal

from django.core.files.base import ContentFile
from django.utils import timezone

from warehouse.models import MovementPlan


ZERO = Decimal("0.000")


def _to_decimal(value) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def build_movement_plan_invoice_snapshot(plan: MovementPlan) -> list[dict]:
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
        else:
            source_location = unit.location
            source_storage_place_id = None

        key = (
            inventory_item.id,
            source_location.id,
            source_storage_place_id,
        )

        if key not in source_lines:
            source_lines[key] = {
                "inventory_item_id": inventory_item.id,
                "source_location_id": source_location.id,
                "source_storage_place_id": source_storage_place_id,
                "quantity": ZERO,
                "unit_symbol": inventory_item.unit.symbol,
                "has_split": False,
            }

        source_lines[key]["quantity"] += _to_decimal(quantity)
        source_lines[key]["has_split"] = (
            source_lines[key]["has_split"] or item.requires_split
        )

    snapshot = list(source_lines.values())
    snapshot.sort(
        key=lambda row: (
            row["inventory_item_id"],
            row["source_location_id"],
            row["source_storage_place_id"] or 0,
        )
    )

    return snapshot


def calculate_movement_plan_invoice_hash(plan: MovementPlan) -> str:
    snapshot = build_movement_plan_invoice_snapshot(plan)

    normalized_snapshot = [
        {
            **row,
            "quantity": str(_to_decimal(row["quantity"]).quantize(Decimal("0.001"))),
        }
        for row in snapshot
    ]

    payload = json.dumps(
        normalized_snapshot,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_movement_plan_invoice_actual(plan: MovementPlan) -> bool:
    if not plan.invoice_file:
        return False

    if not plan.invoice_generated_at:
        return False

    if not plan.invoice_snapshot_hash:
        return False

    return plan.invoice_snapshot_hash == calculate_movement_plan_invoice_hash(plan)


def generate_and_save_movement_plan_invoice(plan: MovementPlan) -> MovementPlan:
    from warehouse.services.movement_plan_invoice_pdf import generate_movement_plan_invoice_pdf

    pdf = generate_movement_plan_invoice_pdf(plan)
    snapshot_hash = calculate_movement_plan_invoice_hash(plan)

    filename = f"movement-plan-{plan.id}-invoice.pdf"

    plan.invoice_file.save(
        filename,
        ContentFile(pdf),
        save=False,
    )
    plan.invoice_generated_at = timezone.now()
    plan.invoice_snapshot_hash = snapshot_hash
    plan.save(
        update_fields=[
            "invoice_file",
            "invoice_generated_at",
            "invoice_snapshot_hash",
        ]
    )

    return plan