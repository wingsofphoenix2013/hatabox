from django.db import models

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import ModelViewSet

from .models import WarehouseLocation, WarehouseStoragePlace
from .serializers import WarehouseLocationSerializer, WarehouseStoragePlaceSerializer


class WarehouseLocationViewSet(ModelViewSet):
    queryset = WarehouseLocation.objects.order_by("code", "id")
    serializer_class = WarehouseLocationSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(code__icontains=search)
                | models.Q(name__icontains=search)
                | models.Q(address__icontains=search)
                | models.Q(comment__icontains=search)
            )

        return queryset


class WarehouseStoragePlaceViewSet(ModelViewSet):
    queryset = WarehouseStoragePlace.objects.select_related(
        "location",
        "parent",
        "parent__location",
    ).order_by("place_type", "code", "id")
    serializer_class = WarehouseStoragePlaceSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

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
                | models.Q(qr_code__icontains=search)
                | models.Q(location__code__icontains=search)
                | models.Q(parent__code__icontains=search)
            )

        return queryset