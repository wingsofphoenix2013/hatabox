from sales.models import SalesOrderEvent


def create_sales_order_event(
    *,
    sales_order,
    event_type,
    title,
    message="",
    payload=None,
    created_by=None,
):
    return SalesOrderEvent.objects.create(
        sales_order=sales_order,
        event_type=event_type,
        title=title,
        message=message,
        payload=payload or {},
        created_by=created_by,
    )