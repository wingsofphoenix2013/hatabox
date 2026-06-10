from django.db import transaction
from django.core.exceptions import ValidationError

from storage.models import StoragePlace


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

    if current_default and current_default.id != storage_place.id:
        current_default._allow_unset_default = True
        current_default.is_default = False
        current_default.save()

    storage_place.is_default = True
    storage_place.is_active = True
    storage_place.save()

    return storage_place