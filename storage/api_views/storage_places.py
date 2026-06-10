from django.db import models

from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from storage.models import (
    StoragePlace,
    StoragePlacePreferredItem,
)
from storage.serializers import (
    StoragePlaceSerializer,
    StoragePlacePreferredItemSerializer,
)
from storage.services.default_place import set_default_storage_place


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
        queryset = self.queryset

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

    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, pk=None):
        storage_place = self.get_object()
        storage_place = set_default_storage_place(storage_place)

        serializer = self.get_serializer(storage_place)
        return Response(serializer.data)


class StoragePlacePreferredItemViewSet(ModelViewSet):
    queryset = StoragePlacePreferredItem.objects.select_related(
        "storage_place",
        "inv_item",
        "inv_item__unit",
    )
    serializer_class = StoragePlacePreferredItemSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        storage_place = self.request.query_params.getlist("storage_place")
        if storage_place:
            queryset = queryset.filter(storage_place_id__in=storage_place)

        inv_item = self.request.query_params.getlist("inv_item")
        if inv_item:
            queryset = queryset.filter(inv_item_id__in=inv_item)

        return queryset