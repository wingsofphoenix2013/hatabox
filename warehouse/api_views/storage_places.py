from warehouse.services.storage_places import sort_storage_places_hierarchically

from django.db import models
from django.db.models import Case, CharField, F, Value, When
from django.db.models.functions import Concat

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from warehouse.models import WarehouseStoragePlace
from warehouse.serializers import WarehouseStoragePlaceSerializer

class WarehouseStoragePlaceViewSet(ModelViewSet):
    queryset = WarehouseStoragePlace.objects.select_related(
        "location",
        "parent",
        "parent__location",
        "parent__parent",
        "parent__parent__location",
        "parent__parent__parent",
        "parent__parent__parent__location",
    )
    serializer_class = WarehouseStoragePlaceSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self._with_display_name_search_annotation(self.queryset)

        location = self.request.query_params.getlist("location")
        if location:
            queryset = queryset.filter(location_id__in=location)

        parent = self.request.query_params.getlist("parent")
        if parent:
            queryset = queryset.filter(parent_id__in=parent)

        place_type = self.request.query_params.getlist("place_type")
        if place_type:
            queryset = queryset.filter(place_type__in=place_type)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(code__icontains=search)
                | models.Q(name__icontains=search)
                | models.Q(comment__icontains=search)
                | models.Q(location__code__icontains=search)
                | models.Q(parent__code__icontains=search)
                | models.Q(display_name_search__icontains=search)
            )

        return queryset
        
    def _with_display_name_search_annotation(self, queryset):
        return queryset.annotate(
            display_name_search=Case(
                When(
                    parent__isnull=True,
                    place_type=WarehouseStoragePlace.PlaceType.CONTAINER,
                    then=Concat(
                        F("location__code"),
                        F("code"),
                        output_field=CharField(),
                    ),
                ),
                When(
                    parent__isnull=True,
                    then=Concat(
                        F("location__code"),
                        Value("-"),
                        F("code"),
                        output_field=CharField(),
                    ),
                ),
                When(
                    parent__parent__isnull=True,
                    parent__place_type=WarehouseStoragePlace.PlaceType.CONTAINER,
                    then=Concat(
                        F("location__code"),
                        F("parent__code"),
                        Value("-"),
                        F("code"),
                        output_field=CharField(),
                    ),
                ),
                When(
                    parent__parent__isnull=True,
                    then=Concat(
                        F("location__code"),
                        Value("-"),
                        F("parent__code"),
                        Value("-"),
                        F("code"),
                        output_field=CharField(),
                    ),
                ),
                When(
                    parent__parent__parent__isnull=True,
                    parent__parent__place_type=WarehouseStoragePlace.PlaceType.CONTAINER,
                    then=Concat(
                        F("location__code"),
                        F("parent__parent__code"),
                        Value("-"),
                        F("parent__code"),
                        Value("-"),
                        F("code"),
                        output_field=CharField(),
                    ),
                ),
                When(
                    parent__parent__parent__isnull=True,
                    then=Concat(
                        F("location__code"),
                        Value("-"),
                        F("parent__parent__code"),
                        Value("-"),
                        F("parent__code"),
                        Value("-"),
                        F("code"),
                        output_field=CharField(),
                    ),
                ),
                default=Case(
                    When(
                        parent__parent__parent__place_type=WarehouseStoragePlace.PlaceType.CONTAINER,
                        then=Concat(
                            F("location__code"),
                            F("parent__parent__parent__code"),
                            Value("-"),
                            F("parent__parent__code"),
                            Value("-"),
                            F("parent__code"),
                            Value("-"),
                            F("code"),
                            output_field=CharField(),
                        ),
                    ),
                    default=Concat(
                        F("location__code"),
                        Value("-"),
                        F("parent__parent__parent__code"),
                        Value("-"),
                        F("parent__parent__code"),
                        Value("-"),
                        F("parent__code"),
                        Value("-"),
                        F("code"),
                        output_field=CharField(),
                    ),
                    output_field=CharField(),
                ),
                output_field=CharField(),
            )
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        ordered_places = sort_storage_places_hierarchically(queryset)

        page = self.paginate_queryset(ordered_places)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(ordered_places, many=True)
        return Response(serializer.data)
