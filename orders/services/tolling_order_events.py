from orders.models import TollingOrderEvent


def create_tolling_order_event(
    *,
    order,
    event_type,
    source,
    title,
    message="",
    payload=None,
    created_by=None,
):
    return TollingOrderEvent.objects.create(
        order=order,
        event_type=event_type,
        source=source,
        title=title,
        message=message,
        payload=payload or {},
        created_by=created_by,
    )