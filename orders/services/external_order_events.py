from orders.models import ExternalOrderEvent


def create_external_order_event(
    *,
    order,
    event_type,
    source,
    title,
    message="",
    payload=None,
    created_by=None,
):
    return ExternalOrderEvent.objects.create(
        order=order,
        event_type=event_type,
        source=source,
        title=title,
        message=message,
        payload=payload or {},
        created_by=created_by,
    )