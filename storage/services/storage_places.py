from collections import OrderedDict

from django.db.models import Count

from storage.models import StoragePlace


def get_storage_place_type_priority(place_type):
    priority_map = {
        StoragePlace.PlaceType.AREA: 0,
        StoragePlace.PlaceType.CONTAINER: 1,
        StoragePlace.PlaceType.RACK: 2,
        StoragePlace.PlaceType.SHELF: 3,
        StoragePlace.PlaceType.BOX: 4,
    }
    return priority_map.get(place_type, 99)


def sort_storage_places_hierarchically(storage_places):
    places = list(storage_places)

    locations = OrderedDict()
    children_map = {}

    for place in places:
        if place.root_location_id:
            locations[place.root_location_id] = place.root_location

        children_map.setdefault(place.parent_id, []).append(place)

    for parent_id in children_map:
        children_map[parent_id].sort(
            key=lambda x: (
                get_storage_place_type_priority(x.place_type),
                x.code,
                x.id,
            )
        )

    ordered = []

    def walk(parent_id, level):
        for child in children_map.get(parent_id, []):
            child.topology_level = level
            child.topology_has_children = bool(children_map.get(child.id))
            ordered.append(child)
            walk(child.id, level + 1)

    for location_id in sorted(
        locations.keys(),
        key=lambda loc_id: (
            locations[loc_id].code,
            locations[loc_id].id,
        ),
    ):
        root_places = [
            place
            for place in places
            if place.root_location_id == location_id
            and place.parent_id is None
        ]

        root_places.sort(
            key=lambda x: (
                get_storage_place_type_priority(x.place_type),
                x.code,
                x.id,
            )
        )

        for root in root_places:
            root.topology_level = 0
            root.topology_has_children = bool(children_map.get(root.id))
            ordered.append(root)
            walk(root.id, 1)

    return ordered


def is_allowed_parent_for_place_type(
    *,
    parent,
    place_type,
):
    if place_type in [
        StoragePlace.PlaceType.AREA,
        StoragePlace.PlaceType.CONTAINER,
    ]:
        return False

    if place_type == StoragePlace.PlaceType.RACK:
        return parent.place_type == StoragePlace.PlaceType.CONTAINER

    if place_type == StoragePlace.PlaceType.SHELF:
        return parent.place_type in [
            StoragePlace.PlaceType.CONTAINER,
            StoragePlace.PlaceType.RACK,
        ]

    if place_type == StoragePlace.PlaceType.BOX:
        if parent.place_type in [
            StoragePlace.PlaceType.CONTAINER,
            StoragePlace.PlaceType.RACK,
            StoragePlace.PlaceType.SHELF,
        ]:
            return True

        if parent.place_type == StoragePlace.PlaceType.BOX:
            return (
                parent.parent is None
                or parent.parent.place_type != StoragePlace.PlaceType.BOX
            )

    return False


def get_storage_place_children_for_parent_options(
    *,
    location,
    parent=None,
):
    queryset = (
        StoragePlace.objects
        .filter(
            root_location=location,
            is_active=True,
            parent=parent,
        )
        .select_related(
            "parent",
        )
        .annotate(
            children_count=Count("children"),
        )
    )

    return sort_storage_places_hierarchically(queryset)