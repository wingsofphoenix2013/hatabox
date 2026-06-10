from django.db import transaction
from django.core.exceptions import ValidationError

from storage.models import StoragePlace, StoragePlaceEvent
from storage.services.events import create_storage_place_event


@transaction.atomic
def set_default_storage_place(storage_place):
    if storage_place.place_type != StoragePlace.PlaceType.AREA:
        raise ValidationError(
            "Місцем за замовчуванням може бути лише площадка."
        )

    location = storage_place.get_root_location()

    current_default = None

    for place in StoragePlace.objects.select_for_update().filter(
        is_default=True,
        place_type=StoragePlace.PlaceType.AREA,
    ):
        if place.get_root_location().id == location.id:
            current_default = place
            break

    old_default_id = current_default.id if current_default else None

    if current_default and current_default.id != storage_place.id:
        current_default._allow_unset_default = True
        current_default.is_default = False
        current_default.save()

    storage_place.is_default = True
    storage_place.is_active = True
    storage_place.save()

    if old_default_id != storage_place.id:
        create_storage_place_event(
            storage_place=storage_place,
            event_type=StoragePlaceEvent.EventType.DEFAULT_CHANGED,
            payload={
                "old": {
                    "default_storage_place_id": old_default_id,
                },
                "new": {
                    "default_storage_place_id": storage_place.id,
                },
            },
        )

    return storage_place