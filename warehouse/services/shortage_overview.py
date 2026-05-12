from django.db.models import Q

from warehouse.models import WarehouseSalesOrderShortage


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

    shortage_rows = shortage_queryset.order_by(
        "inv_item__name",
        "inv_item_id",
    )

    return [
        {
            "inv_item": row.inv_item_id,
            "inv_item_code": row.inv_item.internal_code,
            "inv_item_name": row.inv_item.name,
            "inventory_item_unit_symbol": row.inv_item.unit.symbol,
            "required_quantity": row.required_quantity,
            "available_quantity": row.available_quantity,
            "missing_quantity": row.missing_quantity,
            "last_recalculated_at": row.last_recalculated_at,
        }
        for row in shortage_rows
    ]