from django.db import models

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

from warehouse.models import WarehouseStoragePlace, WarehouseUnit
from warehouse.serializers import WarehouseLocationDetailSerializer
from collections import defaultdict
from decimal import Decimal

from ..models import WarehouseLocation
from ..serializers import WarehouseLocationSerializer


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

    @action(detail=True, methods=["get"], url_path="detail-view")
    def detail_view(self, request, pk=None):
        location = self.get_object()

        storage_places = WarehouseStoragePlace.objects.filter(
            location=location,
            is_active=True,
        )

        units = WarehouseUnit.objects.select_related(
            "inventory_item",
            "inventory_item__unit",
        ).filter(
            location=location,
            storage_place__isnull=True,
            is_active=True,
        )

        grouped = {}
        
        for unit in units:
            item_id = unit.inventory_item_id

            if item_id not in grouped:
                grouped[item_id] = {
                    "inventory_item_id": unit.inventory_item.id,
                    "inventory_item_code": unit.inventory_item.internal_code,
                    "inventory_item_name": unit.inventory_item.name,
                    "inventory_item_unit_symbol": unit.inventory_item.unit.symbol,
                    "quantity": Decimal("0.000"),
                }

            grouped[item_id]["quantity"] += unit.quantity

        direct_stock = list(grouped.values())

        data = {
            "location": {
                "id": location.id,
                "code": location.code,
                "name": location.name,
                "address": location.address,
                "comment": location.comment,
                "is_active": location.is_active,
            },
            "storage_places": storage_places,
            "direct_stock": direct_stock,
        }

        serializer = WarehouseLocationDetailSerializer(data)
        return Response(serializer.data)
