from storage.models import StoragePlaceEvent


def create_storage_place_event(
    *,
    storage_place,
    event_type,
    payload=None,
    created_by=None,
    comment="",
):
    return StoragePlaceEvent.objects.create(
        storage_place=storage_place,
        event_type=event_type,
        payload=payload or {},
        created_by=created_by,
        comment=comment,
    )