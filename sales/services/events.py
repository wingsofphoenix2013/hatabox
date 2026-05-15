from sales.models import SalesOrderEvent


def create_sales_order_event(
    *,
    sales_order,
    event_type,
    source,
    title,
    message="",
    payload=None,
    created_by=None,
):
    return SalesOrderEvent.objects.create(
        sales_order=sales_order,
        event_type=event_type,
        source=source,
        title=title,
        message=message,
        payload=payload or {},
        created_by=created_by,
    )
    
def build_sales_order_events(
    *,
    sales_order,
):
    events = sales_order.events.select_related(
        "created_by",
    ).order_by(
        "-created_at",
        "-id",
    )

    return [
        {
            "id": event.id,

            "event_type": event.event_type,

            "source": event.source,
            "source_display": event.get_source_display(),

            "title": event.title,
            "message": event.message,

            "payload": event.payload,

            "created_by": event.created_by_id,
            "created_by_username": (
                event.created_by.username
                if event.created_by
                else None
            ),

            "created_at": event.created_at,
        }
        for event in events
    ]