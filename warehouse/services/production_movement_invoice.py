from collections import defaultdict
from decimal import Decimal

from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

from warehouse.models import (
    WarehouseProductionMovement,
)


ZERO = Decimal("0.000")


def _to_decimal(value) -> Decimal:
    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def build_production_movement_invoice_context(
    movement: WarehouseProductionMovement,
):
    rows = []
    resize_map = defaultdict(list)

    items = movement.items.select_related(
        "inventory_item",
        "inventory_item__unit",
    ).order_by(
        "inventory_item__name",
        "id",
    )

    for item in items:
        rows.append({
            "inventory_item_name": item.inventory_item.name,
            "source_location_code": (
                item.executed_source_location_code
            ),
            "source_location_name": (
                item.executed_source_location_name
            ),
            "source_storage_place_full_display": (
                item.executed_source_storage_place_full_display
            ),
            "quantity": item.quantity,
            "unit_symbol": item.inventory_item.unit.symbol,
        })

        source_quantity = _to_decimal(
            item.source_warehouse_unit.quantity
        )

        if source_quantity != _to_decimal(item.quantity):
            resize_map[item.inventory_item_id].append(item)

    resize_rows = []

    for inventory_item_id, resize_items in resize_map.items():
        inventory_item = resize_items[0].inventory_item

        resize_rows.append({
            "inventory_item_name": inventory_item.name,
            "source_quantity_text": " + ".join(
                [
                    (
                        f"{_to_decimal(item.quantity).normalize()} "
                        f"{inventory_item.unit.symbol}"
                    )
                    for item in resize_items
                ]
            ),
            "target_quantity_text": (
                f"{sum((_to_decimal(item.quantity) for item in resize_items), ZERO).normalize()} "
                f"{inventory_item.unit.symbol}"
            ),
        })

    return {
        "movement_id": movement.id,
        "invoice_generated_at": timezone.now(),
        "serial_number": (
            movement.production_order.serial_number
        ),
        "step_sequence_number": (
            movement.production_order_step.sequence_number
        ),
        "step_name": (
            movement.production_order_step.name
        ),
        "rows": rows,
        "resize_rows": resize_rows,
    }


def generate_production_movement_invoice_pdf(
    movement: WarehouseProductionMovement,
) -> bytes:
    from weasyprint import HTML

    context = build_production_movement_invoice_context(
        movement,
    )

    html_string = render_to_string(
        "production/production_movement_invoice.html",
        context,
    )

    return HTML(
        string=html_string,
    ).write_pdf()


def generate_and_save_production_movement_invoice(
    movement: WarehouseProductionMovement,
):
    pdf = generate_production_movement_invoice_pdf(
        movement,
    )

    filename = (
        f"production-movement-{movement.id}-invoice.pdf"
    )

    movement.invoice_file.save(
        filename,
        ContentFile(pdf),
        save=False,
    )

    movement.invoice_generated_at = timezone.now()

    movement.save(
        update_fields=[
            "invoice_file",
            "invoice_generated_at",
        ]
    )

    return movement