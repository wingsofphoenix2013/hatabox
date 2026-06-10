from django.db import models

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import ModelViewSet

from storage.models import StorageLocation
from storage.serializers import StorageLocationSerializer


class StorageLocationViewSet(ModelViewSet):
    queryset = StorageLocation.objects.order_by("code", "id")
    serializer_class = StorageLocationSerializer
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