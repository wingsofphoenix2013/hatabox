from django.db import models
from django.utils import timezone

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

from warehouse.models import (
    MovementPlan,
    MovementPlanItem,
    WarehouseStoragePlace,
    WarehouseUnit,
)
from warehouse.services.storage_places import sort_storage_places_hierarchically
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

        storage_places_queryset = WarehouseStoragePlace.objects.filter(
            location=location,
            is_active=True,
        )

        storage_places = sort_storage_places_hierarchically(storage_places_queryset)

        reserved_plan_items = MovementPlanItem.objects.select_related(
            "plan",
            "plan__target_location",
            "plan__target_storage_place",
            "plan__target_storage_place__location",
            "warehouse_unit",
            "warehouse_unit__inventory_item",
            "warehouse_unit__inventory_item__unit",
        ).filter(
            warehouse_unit__location=location,
            warehouse_unit__storage_place__isnull=True,
            warehouse_unit__is_active=True,
            plan__status=MovementPlan.Status.ACTIVE,
            is_reserved=True,
        )

        reserved_unit_ids = {
            item.warehouse_unit_id
            for item in reserved_plan_items
        }

        units = WarehouseUnit.objects.select_related(
            "inventory_item",
            "inventory_item__unit",
        ).filter(
            location=location,
            storage_place__isnull=True,
            is_active=True,
        ).exclude(
            id__in=reserved_unit_ids,
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

        reserved_grouped = {}

        for plan_item in reserved_plan_items:
            unit = plan_item.warehouse_unit
            plan = plan_item.plan
            item_id = unit.inventory_item_id

            if plan.target_location is not None:
                target_location = plan.target_location
                target_storage_place_id = None
                target_storage_place_code = None
                target_storage_place_display_name = None
                target_storage_place_full_display = None
            else:
                target_location = plan.target_storage_place.location
                target_storage_place_id = plan.target_storage_place.id
                target_storage_place_code = plan.target_storage_place.code
                target_storage_place_display_name = plan.target_storage_place.get_display_name()
                target_storage_place_full_display = plan.target_storage_place.get_display_name_verbose()

            key = (
                item_id,
                plan.id,
                target_location.id,
                target_storage_place_id,
            )

            if plan.planned_at is None:
                movement_plan_days_delta = None
                movement_plan_is_overdue = False
                movement_plan_planned_status_text = None
            else:
                planned_date = timezone.localtime(plan.planned_at).date()
                today = timezone.localdate()
                movement_plan_days_delta = (planned_date - today).days
                movement_plan_is_overdue = movement_plan_days_delta < 0

                if movement_plan_days_delta < 0:
                    movement_plan_planned_status_text = (
                        f"Просрочено на {abs(movement_plan_days_delta)} дн."
                    )
                elif movement_plan_days_delta == 0:
                    movement_plan_planned_status_text = "Сьогодні"
                else:
                    movement_plan_planned_status_text = (
                        f"Осталось {movement_plan_days_delta} дн."
                    )

            if key not in reserved_grouped:
                reserved_grouped[key] = {
                    "inventory_item_id": unit.inventory_item.id,
                    "inventory_item_code": unit.inventory_item.internal_code,
                    "inventory_item_name": unit.inventory_item.name,
                    "inventory_item_unit_symbol": unit.inventory_item.unit.symbol,
                    "quantity": Decimal("0.000"),
                    "movement_plan_id": plan.id,
                    "movement_plan_status": plan.status,
                    "movement_plan_created_at": plan.created_at,
                    "movement_plan_planned_at": plan.planned_at,
                    "movement_plan_is_overdue": movement_plan_is_overdue,
                    "movement_plan_days_delta": movement_plan_days_delta,
                    "movement_plan_planned_status_text": movement_plan_planned_status_text,
                    "target_location_id": target_location.id,
                    "target_location_code": target_location.code,
                    "target_location_name": target_location.name,
                    "target_storage_place_id": target_storage_place_id,
                    "target_storage_place_code": target_storage_place_code,
                    "target_storage_place_display_name": target_storage_place_display_name,
                    "target_storage_place_full_display": target_storage_place_full_display,
                }

            reserved_grouped[key]["quantity"] += (
                plan_item.move_quantity
                if plan_item.requires_split
                else plan_item.reserved_quantity
            )

        direct_reserved_stock = list(reserved_grouped.values())

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
            "direct_reserved_stock": direct_reserved_stock,
        }

        serializer = WarehouseLocationDetailSerializer(data)
        return Response(serializer.data)
