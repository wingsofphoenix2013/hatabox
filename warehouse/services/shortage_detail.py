from sales.models import SalesOrder, SalesOrderComponent

from warehouse.models import WarehouseSalesOrderShortage


def build_shortage_detail(
    *,
    inv_item_id,
):
    try:
        shortage = WarehouseSalesOrderShortage.objects.select_related(
            "inv_item",
            "inv_item__unit",
        ).get(
            inv_item_id=inv_item_id,
        )
    except WarehouseSalesOrderShortage.DoesNotExist:
        return None

    inv_item = shortage.inv_item

    components = list(
        SalesOrderComponent.objects.select_related(
            "sales_order",
            "sales_order__organization",
            "sales_order__product",
            "sales_order__product__product_family",
        ).filter(
            sales_order__status=SalesOrder.Status.CONFIRMED,
            fulfillment_mode=SalesOrderComponent.FulfillmentMode.MIXED,
            inv_item_id=inv_item_id,
        ).order_by(
            "sales_order__created_at",
            "sales_order_id",
            "id",
        )
    )

    sales_order_ids = {
        component.sales_order_id
        for component in components
    }

    return {
        "inv_item": inv_item.id,
        "inv_item_code": inv_item.internal_code,
        "inv_item_name": inv_item.name,
        "inventory_item_unit_symbol": inv_item.unit.symbol,

        "summary": {
            "required_quantity": shortage.required_quantity,
            "available_quantity": shortage.available_quantity,
            "missing_quantity": shortage.missing_quantity,
            "sales_orders_count": len(sales_order_ids),
            "last_recalculated_at": shortage.last_recalculated_at,
        },

        "rows": [
            {
                "sales_order": component.sales_order.id,
                "sales_order_status": component.sales_order.status,
                "sales_order_created_at": component.sales_order.created_at,

                "organization": component.sales_order.organization.id,
                "organization_name": component.sales_order.organization.name,

                "product": component.sales_order.product.id,
                "product_code": component.sales_order.product.code,
                "product_name": component.sales_order.product.product_family.name,

                "component_id": component.id,

                "required_quantity": component.quantity,
            }
            for component in components
        ],
    }