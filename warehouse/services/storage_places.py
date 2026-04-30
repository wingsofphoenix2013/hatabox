from collections import OrderedDict

from warehouse.models import WarehouseStoragePlace


def get_storage_place_type_priority(place_type):
    priority_map = {
        WarehouseStoragePlace.PlaceType.CONTAINER: 0,
        WarehouseStoragePlace.PlaceType.RACK: 1,
        WarehouseStoragePlace.PlaceType.BOX: 2,
    }
    return priority_map.get(place_type, 99)


def sort_storage_places_hierarchically(storage_places):
    places = list(storage_places)

    locations = OrderedDict()
    children_map = {}

    for place in places:
        locations[place.location_id] = place.location
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

    def walk(parent_id):
        for child in children_map.get(parent_id, []):
            ordered.append(child)
            walk(child.id)

    place_ids = {place.id for place in places}

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
            if place.location_id == location_id
            and (place.parent_id is None or place.parent_id not in place_ids)
        ]

        root_places.sort(
            key=lambda x: (
                get_storage_place_type_priority(x.place_type),
                x.code,
                x.id,
            )
        )

        for root in root_places:
            ordered.append(root)
            walk(root.id)

    return ordered