from django.db.models import Count, Sum
from rest_framework.exceptions import ValidationError

from production.models import (
    ProductionOrderMaterialSnapshot,
    ProductionOrderMaterialSnapshotItem,
)


def build_production_order_material_snapshot_report(
    *,
    production_order,
):
    try:
        snapshot = production_order.material_snapshot
    except ProductionOrderMaterialSnapshot.DoesNotExist:
        raise ValidationError(
            "Snapshot матеріалів для цього ProductionOrder ще не створено."
        )

    items = snapshot.items.select_related(
        "inv_item",
        "inv_item__unit",
        "external_order",
        "vendor",
        "vendor_item",
        "tolling_source_order_item",
        "tolling_source_order_item__order",
        "tolling_source_order_item__order__organization",
    )

    own_components = list(
        items.filter(
            origin_type=ProductionOrderMaterialSnapshotItem.OriginType.OWN,
        ).values(
            "inv_item_id",
            "inv_item__internal_code",
            "inv_item__name",
            "inv_item__unit__symbol",
            "external_order_id",
            "external_order_no",
            "vendor_id",
            "vendor_name",
            "vendor_item_id",
            "vendor_sku",
            "unit_price",
            "prices_include_vat",
            "vat_rate",
        ).annotate(
            quantity=Sum("quantity"),
            cost_without_vat=Sum("cost_without_vat"),
            vat_amount=Sum("vat_amount"),
            cost_with_vat=Sum("cost_with_vat"),
            warehouse_units_count=Count("warehouse_unit_id"),
        ).order_by(
            "inv_item__name",
            "external_order_no",
            "vendor_name",
        )
    )

    donor_components = list(
        items.filter(
            origin_type=ProductionOrderMaterialSnapshotItem.OriginType.DONOR,
        ).values(
            "inv_item_id",
            "inv_item__internal_code",
            "inv_item__name",
            "inv_item__unit__symbol",
            "tolling_source_order_item_id",
            "tolling_source_order_item__order_id",
            "tolling_source_order_item__order__order_no",
            "tolling_source_order_item__order__organization_id",
            "tolling_source_order_item__order__organization__name",
        ).annotate(
            quantity=Sum("quantity"),
            warehouse_units_count=Count("warehouse_unit_id"),
        ).order_by(
            "inv_item__name",
            "tolling_source_order_item__order__order_no",
        )
    )

    customer_components = list(
        items.filter(
            origin_type=ProductionOrderMaterialSnapshotItem.OriginType.CUSTOMER,
        ).values(
            "inv_item_id",
            "inv_item__internal_code",
            "inv_item__name",
            "inv_item__unit__symbol",
            "tolling_source_order_item_id",
            "tolling_source_order_item__order_id",
            "tolling_source_order_item__order__order_no",
            "tolling_source_order_item__order__organization_id",
            "tolling_source_order_item__order__organization__name",
        ).annotate(
            quantity=Sum("quantity"),
            warehouse_units_count=Count("warehouse_unit_id"),
        ).order_by(
            "inv_item__name",
            "tolling_source_order_item__order__order_no",
        )
    )

    summary = items.aggregate(
        total_items_count=Count("id"),
        total_warehouse_units_count=Count("warehouse_unit_id"),
        total_cost_without_vat=Sum("cost_without_vat"),
        total_vat_amount=Sum("vat_amount"),
        total_cost_with_vat=Sum("cost_with_vat"),
    )

    summary["unique_components_count"] = (
        items.values(
            "inv_item_id",
        ).distinct().count()
    )

    summary.update({
        "snapshot": snapshot.id,
        "snapshot_status": snapshot.status,
        "calculated_at": snapshot.calculated_at,
        "production_order": production_order.id,
        "production_order_status": production_order.status,
        "sales_order": production_order.sales_order_id,
        "serial_number": production_order.serial_number,
        "ready_at": production_order.ready_at,
        "own_rows_count": len(own_components),
        "donor_rows_count": len(donor_components),
        "customer_rows_count": len(customer_components),
    })

    return {
        "summary": summary,
        "own_components": own_components,
        "donor_components": donor_components,
        "customer_components": customer_components,
    }