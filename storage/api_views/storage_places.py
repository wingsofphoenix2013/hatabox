from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Exists, OuterRef

from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from storage.models import (
    StorageLocation,
    StoragePlace,
    StoragePlacePreferredItem,
    StoragePlaceEvent,
)
from storage.serializers import (
    StoragePlaceSerializer,
    StoragePlacePreferredItemSerializer,
    StoragePlaceSummarySerializer,
    StoragePlaceParentOptionSerializer,
    StoragePlaceDetailSerializer,
    StorageChildTypeOptionSerializer,
)
from storage.services.default_place import set_default_storage_place
from storage.services.storage_places import (
    get_storage_place_children_for_parent_options,
    is_allowed_parent_for_place_type,
    sort_storage_places_hierarchically,
)


class StoragePlaceViewSet(ModelViewSet):
    queryset = StoragePlace.objects.select_related(
        "location",
        "parent",
    ).prefetch_related(
        "preferred_items",
        "preferred_items__inv_item",
    )
    serializer_class = StoragePlaceSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset.all()

        place_type = self.request.query_params.getlist("place_type")
        if place_type:
            queryset = queryset.filter(place_type__in=place_type)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        is_default = self.request.query_params.get("is_default")
        if is_default is not None:
            queryset = queryset.filter(is_default=is_default.lower() == "true")

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(code__icontains=search)
                | models.Q(address__icontains=search)
                | models.Q(name__icontains=search)
                | models.Q(comment__icontains=search)
            )

        return queryset

    @action(detail=True, methods=["get"], url_path="detail-view")
    def detail_view(self, request, pk=None):
        storage_place = self.get_object()

        preferred_items = StoragePlacePreferredItem.objects.select_related(
            "inv_item",
        ).filter(
            storage_place=storage_place,
        )

        events = StoragePlaceEvent.objects.filter(
            storage_place=storage_place,
        ).order_by(
            "-created_at",
            "-id",
        )[:20]

        data = {
            "summary": {
                "id": storage_place.id,
                "location_id": storage_place.root_location.id,
                "location_code": storage_place.root_location.code,
                "location_name": storage_place.root_location.name,
                "parent_id": storage_place.parent_id,
                "parent_address": (
                    storage_place.parent.address
                    if storage_place.parent
                    else None
                ),
                "code": storage_place.code,
                "address": storage_place.address,
                "address_verbose": storage_place.address_verbose,
                "place_type": storage_place.place_type,
                "place_type_name": storage_place.get_place_type_display(),
                "name": storage_place.name,
                "comment": storage_place.comment,
                "is_active": storage_place.is_active,
                "is_default": storage_place.is_default,
                "can_set_default": storage_place.can_be_set_default(),
                "can_activate": storage_place.can_be_activated(),
                "activate_block_reason": storage_place.get_activate_block_reason(),
                "can_deactivate": storage_place.can_be_deactivated(),
                "deactivate_block_reason": storage_place.get_deactivate_block_reason(),
                "can_add_inside": storage_place.can_add_inside(),
                "has_children": storage_place.has_children(),
            },
            "preferred_items": preferred_items,
            "events": [
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "event_type_name": event.get_event_type_display(),
                    "payload": event.payload,
                    "created_at": event.created_at,
                    "comment": event.comment,
                }
                for event in events
            ],
        }

        serializer = StoragePlaceDetailSerializer(data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        storage_place = self.get_object()

        storage_place.is_active = True
        storage_place.save()

        serializer = self.get_serializer(storage_place)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        storage_place = self.get_object()

        storage_place.is_active = False
        storage_place.save()

        serializer = self.get_serializer(storage_place)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, pk=None):
        storage_place = self.get_object()
        storage_place = set_default_storage_place(storage_place)

        serializer = self.get_serializer(storage_place)
        return Response(serializer.data)


class StoragePlacePreferredItemViewSet(ModelViewSet):
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            instance.delete()
        except ValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=400,
            )

        return Response(status=204)

    queryset = StoragePlacePreferredItem.objects.select_related(
        "storage_place",
        "inv_item",
        "inv_item__unit",
    )
    serializer_class = StoragePlacePreferredItemSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset.all()

        storage_place = self.request.query_params.getlist("storage_place")
        if storage_place:
            queryset = queryset.filter(storage_place_id__in=storage_place)

        inv_item = self.request.query_params.getlist("inv_item")
        if inv_item:
            queryset = queryset.filter(inv_item_id__in=inv_item)

        return queryset
        
class StoragePlaceSummaryViewSet(ReadOnlyModelViewSet):
    serializer_class = StoragePlaceSummarySerializer
    permission_classes = [DjangoModelPermissions]

    queryset = (
        StoragePlace.objects
        .select_related(
            "root_location",
        )
        .prefetch_related(
            "preferred_items",
            "preferred_items__inv_item",
            "preferred_items__inv_item__category",
        )
        .annotate(
            preferred_items_count=Count("preferred_items"),
        )
        .order_by(
            "root_location__code",
            "parent_id",
            "code",
            "id",
        )
    )

    def get_queryset(self):
        queryset = self.queryset.all()

        location = self.request.query_params.getlist("location")
        if location:
            queryset = queryset.filter(root_location_id__in=location)

        place_type = self.request.query_params.getlist("place_type")
        if place_type:
            queryset = queryset.filter(place_type__in=place_type)

        is_active = self.request.query_params.get("is_active")
        if is_active is None:
            queryset = queryset.filter(is_active=True)
        else:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        search = self.request.query_params.get("search")
        if search:
            matching_preferred_items = StoragePlacePreferredItem.objects.filter(
                storage_place_id=OuterRef("pk"),
            ).filter(
                models.Q(inv_item__name__icontains=search)
                | models.Q(inv_item__internal_code__icontains=search)
            )

            queryset = queryset.annotate(
                has_matching_preferred_item=Exists(matching_preferred_items),
            ).filter(
                models.Q(code__icontains=search)
                | models.Q(address__icontains=search)
                | models.Q(name__icontains=search)
                | models.Q(has_matching_preferred_item=True)
            )

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        if (
            request.query_params.get("search")
            or request.query_params.get("is_active") == "false"
            or request.query_params.getlist("place_type")
        ):
            ordered_places = list(queryset.order_by(
                "root_location__code",
                "address",
                "id",
            ))

            for place in ordered_places:
                place.topology_level = max(place.address.count("-") - 1, 0)
                place.topology_has_children = place.children.exists()
        else:
            ordered_places = sort_storage_places_hierarchically(queryset)

        page = self.paginate_queryset(ordered_places)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(ordered_places, many=True)
        return Response(serializer.data)
        
class StoragePlaceParentOptionViewSet(ReadOnlyModelViewSet):
    queryset = StoragePlace.objects.all()
    serializer_class = StoragePlaceParentOptionSerializer
    permission_classes = [DjangoModelPermissions]

    def list(self, request, *args, **kwargs):
        location_id = request.query_params.get("location")
        place_type = request.query_params.get("place_type")
        parent_id = request.query_params.get("parent")

        if not location_id:
            return Response(
                {"detail": "Потрібно вказати location."},
                status=400,
            )

        if not place_type:
            return Response(
                {"detail": "Потрібно вказати place_type."},
                status=400,
            )

        location = StorageLocation.objects.get(pk=location_id)

        parent = None
        if parent_id:
            parent = StoragePlace.objects.get(
                pk=parent_id,
                root_location=location,
                is_active=True,
            )

        options = []

        can_create_here = (
            parent is None
            and place_type in [
                StoragePlace.PlaceType.AREA,
                StoragePlace.PlaceType.CONTAINER,
                StoragePlace.PlaceType.RACK,
                StoragePlace.PlaceType.BOX,
            ]
        ) or (
            parent is not None
            and is_allowed_parent_for_place_type(
                parent=parent,
                place_type=place_type,
            )
        )

        if can_create_here:
            options.append({
                "id": None,
                "address": None,
                "address_verbose": None,
                "place_type": None,
                "place_type_name": None,
                "level": 0,
                "has_children": False,
                "label": (
                    "Створити прямо на локації"
                    if parent is None
                    else "Створити в цьому об'єкті"
                ),
            })

        if place_type in [
            StoragePlace.PlaceType.AREA,
            StoragePlace.PlaceType.CONTAINER,
        ]:
            serializer = self.get_serializer(options, many=True)
            return Response(serializer.data)

        children = get_storage_place_children_for_parent_options(
            location=location,
            place_type=place_type,
            parent=parent,
        )

        for child in children:
            options.append({
                "id": child.id,
                "address": child.address,
                "address_verbose": child.address_verbose,
                "place_type": child.place_type,
                "place_type_name": child.get_place_type_display(),
                "level": getattr(child, "topology_level", 0),
                "has_children": child.children_count > 0,
                "label": f"{child.address} — {child.get_place_type_display()} {child.code}",
            })

        serializer = self.get_serializer(options, many=True)
        return Response(serializer.data)
        
class StorageChildTypeOptionViewSet(ReadOnlyModelViewSet):
    queryset = StoragePlace.objects.all()
    serializer_class = StorageChildTypeOptionSerializer
    permission_classes = [DjangoModelPermissions]

    def list(self, request, *args, **kwargs):
        parent_id = request.query_params.get("parent")

        if not parent_id:
            return Response(
                {"detail": "Потрібно вказати parent."},
                status=400,
            )

        parent = StoragePlace.objects.get(pk=parent_id)

        if not parent.is_active:
            return Response(
                {
                    "detail": (
                        "Неможливо створити вкладене місце "
                        "в неактивному місці зберігання."
                    )
                },
                status=400,
            )

        options = []

        if parent.place_type == StoragePlace.PlaceType.CONTAINER:
            options.extend([
                {"value": "rack", "label": "Стелаж"},
                {"value": "shelf", "label": "Полка"},
                {"value": "box", "label": "Коробка"},
            ])

        elif parent.place_type == StoragePlace.PlaceType.RACK:
            options.extend([
                {"value": "shelf", "label": "Полка"},
                {"value": "box", "label": "Коробка"},
            ])

        elif parent.place_type == StoragePlace.PlaceType.SHELF:
            options.append(
                {"value": "box", "label": "Коробка"}
            )

        elif parent.place_type == StoragePlace.PlaceType.BOX:
            if (
                parent.parent is None
                or parent.parent.place_type != StoragePlace.PlaceType.BOX
            ):
                options.append(
                    {"value": "box", "label": "Коробка"}
                )

        serializer = self.get_serializer(options, many=True)
        return Response(serializer.data)