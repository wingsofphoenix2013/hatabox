from warehouse.services.storage_places import sort_storage_places_hierarchically

from django.db import models
from django.db.models import Case, CharField, F, Value, When
from django.db.models.deletion import ProtectedError
from django.db.models.functions import Concat

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action

from collections import defaultdict
from decimal import Decimal
from django.utils import timezone

from warehouse.models import MovementPlan, MovementPlanItem, WarehouseUnit
from warehouse.services.movement_plan_invoice import is_movement_plan_invoice_actual
from warehouse.serializers import WarehouseStoragePlaceDetailSerializer

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
        
    def destroy(self, request, *args, **kwargs):
        storage_place = self.get_object()

        if not storage_place.can_be_deleted():
            raise ValidationError(
                "Неможливо видалити місце зберігання, оскільки воно використовується в складських операціях."
            )

        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            raise ValidationError(
                "Неможливо видалити місце зберігання, оскільки воно має пов'язані об'єкти."
            )
        
    @action(detail=True, methods=["get"], url_path="detail-view")
    def detail_view(self, request, pk=None):
        storage_place = self.get_object()

        # children
        children = WarehouseStoragePlace.objects.filter(
            parent=storage_place,
            is_active=True,
        )

        # direct reserved
        reserved_plan_items = MovementPlanItem.objects.select_related(
            "plan",
            "plan__target_location",
            "plan__target_storage_place",
            "plan__target_storage_place__location",
            "warehouse_unit",
            "warehouse_unit__inventory_item",
            "warehouse_unit__inventory_item__unit",
        ).filter(
            warehouse_unit__storage_place=storage_place,
            warehouse_unit__is_active=True,
            plan__status=MovementPlan.Status.ACTIVE,
            is_reserved=True,
        )

        reserved_unit_ids = {
            item.warehouse_unit_id
            for item in reserved_plan_items
        }

        # direct stock (без reserved)
        units = WarehouseUnit.objects.select_related(
            "inventory_item",
            "inventory_item__unit",
        ).filter(
            storage_place=storage_place,
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

        # reserved stock
        reserved_grouped = {}

        for plan_item in reserved_plan_items:
            unit = plan_item.warehouse_unit
            plan = plan_item.plan
            item_id = unit.inventory_item_id

            if plan.planned_at is None:
                days_delta = None
                is_overdue = False
                status_text = None
            else:
                planned_date = timezone.localtime(plan.planned_at).date()
                today = timezone.localdate()
                days_delta = (planned_date - today).days
                is_overdue = days_delta < 0

                if days_delta < 0:
                    status_text = f"Просрочено на {abs(days_delta)} дн."
                elif days_delta == 0:
                    status_text = "Сьогодні"
                else:
                    status_text = f"Осталось {days_delta} дн."

            key = (item_id, plan.id)

            if key not in reserved_grouped:
                reserved_grouped[key] = {
                    "inventory_item_id": unit.inventory_item.id,
                    "inventory_item_code": unit.inventory_item.internal_code,
                    "inventory_item_name": unit.inventory_item.name,
                    "inventory_item_unit_symbol": unit.inventory_item.unit.symbol,
                    "quantity": Decimal("0.000"),
                    "movement_plan_id": plan.id,
                    "movement_plan_status": plan.status,
                    "movement_plan_can_execute": (
                        plan.status == MovementPlan.Status.ACTIVE
                        and is_movement_plan_invoice_actual(plan)
                        and plan.items.exists()
                    ),
                    "movement_plan_created_at": plan.created_at,
                    "movement_plan_planned_at": plan.planned_at,
                    "movement_plan_is_overdue": is_overdue,
                    "movement_plan_days_delta": days_delta,
                    "movement_plan_planned_status_text": status_text,
                    "target_location_id": plan.target_location.id if plan.target_location else plan.target_storage_place.location.id,
                    "target_location_code": plan.target_location.code if plan.target_location else plan.target_storage_place.location.code,
                    "target_location_name": plan.target_location.name if plan.target_location else plan.target_storage_place.location.name,
                    "target_storage_place_id": plan.target_storage_place.id if plan.target_storage_place else None,
                    "target_storage_place_code": plan.target_storage_place.code if plan.target_storage_place else None,
                    "target_storage_place_display_name": plan.target_storage_place.get_display_name() if plan.target_storage_place else None,
                    "target_storage_place_full_display": plan.target_storage_place.get_display_name_verbose() if plan.target_storage_place else None,
                }

            reserved_grouped[key]["quantity"] += (
                plan_item.move_quantity if plan_item.requires_split else plan_item.reserved_quantity
            )

        direct_reserved_stock = list(reserved_grouped.values())

        # собрать все descendants
        descendants = []
        stack = [storage_place.id]

        while stack:
            current_id = stack.pop()
            children_qs = WarehouseStoragePlace.objects.filter(parent_id=current_id)
            for child in children_qs:
                descendants.append(child.id)
                stack.append(child.id)

        # reserved units во вложенных
        nested_reserved_plan_items = MovementPlanItem.objects.select_related(
            "plan",
            "plan__target_location",
            "plan__target_storage_place",
            "plan__target_storage_place__location",
            "warehouse_unit",
            "warehouse_unit__inventory_item",
            "warehouse_unit__inventory_item__unit",
            "warehouse_unit__storage_place",
        ).filter(
            warehouse_unit__storage_place_id__in=descendants,
            warehouse_unit__is_active=True,
            plan__status=MovementPlan.Status.ACTIVE,
            is_reserved=True,
        )

        nested_reserved_unit_ids = {
            item.warehouse_unit_id for item in nested_reserved_plan_items
        }

        # nested доступный товар
        nested_units = WarehouseUnit.objects.select_related(
            "inventory_item",
            "inventory_item__unit",
            "storage_place",
        ).filter(
            storage_place_id__in=descendants,
            is_active=True,
        ).exclude(
            id__in=nested_reserved_unit_ids,
        )

        nested_grouped = {}

        for unit in nested_units:
            key = (unit.inventory_item_id, unit.storage_place_id)

            if key not in nested_grouped:
                nested_grouped[key] = {
                    "inventory_item_id": unit.inventory_item.id,
                    "inventory_item_code": unit.inventory_item.internal_code,
                    "inventory_item_name": unit.inventory_item.name,
                    "inventory_item_unit_symbol": unit.inventory_item.unit.symbol,
                    "storage_place_id": unit.storage_place.id,
                    "storage_place_code": unit.storage_place.code,
                    "storage_place_display_name": unit.storage_place.get_display_name(),
                    "storage_place_full_display": unit.storage_place.get_display_name_verbose(),
                    "quantity": Decimal("0.000"),
                }

            nested_grouped[key]["quantity"] += unit.quantity

        nested_stock = list(nested_grouped.values())

        # nested reserved
        nested_reserved_grouped = {}

        for plan_item in nested_reserved_plan_items:
            unit = plan_item.warehouse_unit
            plan = plan_item.plan
            key = (unit.inventory_item_id, unit.storage_place_id, plan.id)

            if plan.planned_at is None:
                days_delta = None
                is_overdue = False
                status_text = None
            else:
                planned_date = timezone.localtime(plan.planned_at).date()
                today = timezone.localdate()
                days_delta = (planned_date - today).days
                is_overdue = days_delta < 0

                if days_delta < 0:
                    status_text = f"Просрочено на {abs(days_delta)} дн."
                elif days_delta == 0:
                    status_text = "Сьогодні"
                else:
                    status_text = f"Осталось {days_delta} дн."

            if key not in nested_reserved_grouped:
                nested_reserved_grouped[key] = {
                    "inventory_item_id": unit.inventory_item.id,
                    "inventory_item_code": unit.inventory_item.internal_code,
                    "inventory_item_name": unit.inventory_item.name,
                    "inventory_item_unit_symbol": unit.inventory_item.unit.symbol,
                    "storage_place_id": unit.storage_place.id,
                    "storage_place_code": unit.storage_place.code,
                    "storage_place_display_name": unit.storage_place.get_display_name(),
                    "storage_place_full_display": unit.storage_place.get_display_name_verbose(),
                    "quantity": Decimal("0.000"),
                    "movement_plan_id": plan.id,
                    "movement_plan_status": plan.status,
                    "movement_plan_can_execute": (
                        plan.status == MovementPlan.Status.ACTIVE
                        and is_movement_plan_invoice_actual(plan)
                        and plan.items.exists()
                    ),
                    "movement_plan_created_at": plan.created_at,
                    "movement_plan_planned_at": plan.planned_at,
                    "movement_plan_is_overdue": is_overdue,
                    "movement_plan_days_delta": days_delta,
                    "movement_plan_planned_status_text": status_text,
                    "target_location_id": plan.target_location.id if plan.target_location else plan.target_storage_place.location.id,
                    "target_location_code": plan.target_location.code if plan.target_location else plan.target_storage_place.location.code,
                    "target_location_name": plan.target_location.name if plan.target_location else plan.target_storage_place.location.name,
                    "target_storage_place_id": plan.target_storage_place.id if plan.target_storage_place else None,
                    "target_storage_place_code": plan.target_storage_place.code if plan.target_storage_place else None,
                    "target_storage_place_display_name": plan.target_storage_place.get_display_name() if plan.target_storage_place else None,
                    "target_storage_place_full_display": plan.target_storage_place.get_display_name_verbose() if plan.target_storage_place else None,
                }

            nested_reserved_grouped[key]["quantity"] += (
                plan_item.move_quantity if plan_item.requires_split else plan_item.reserved_quantity
            )

        nested_reserved_stock = list(nested_reserved_grouped.values())

        data = {
            "storage_place": {
                "id": storage_place.id,
                "code": storage_place.code,
                "display_name": storage_place.get_display_name(),
                "display_name_verbose": storage_place.get_display_name_verbose(),
                "place_type": storage_place.place_type,
                "place_type_name": storage_place.get_place_type_display(),
                "parent_storage_place": (
                    {
                        "id": storage_place.parent.id,
                        "display_name": storage_place.parent.get_display_name(),
                        "display_name_verbose": storage_place.parent.get_display_name_verbose(),
                        "place_type": storage_place.parent.place_type,
                        "place_type_name": storage_place.parent.get_place_type_display(),
                    }
                    if storage_place.parent
                    else None
                ),
                "name": storage_place.name,
                "comment": storage_place.comment,
                "image": storage_place.image.url if storage_place.image else None,
                "qr_pdf_file": storage_place.qr_pdf_file.url if storage_place.qr_pdf_file else None,
                "can_delete": storage_place.can_be_deleted(),
                "delete_block_reasons": storage_place.get_delete_block_reasons(),
                "location_id": storage_place.location.id,
                "location_code": storage_place.location.code,
                "location_name": storage_place.location.name,
            },
            "children": WarehouseStoragePlaceSerializer(children, many=True).data,
            "direct_stock": direct_stock,
            "direct_reserved_stock": direct_reserved_stock,
            "nested_stock": nested_stock,
            "nested_reserved_stock": nested_reserved_stock,
        }

        serializer = WarehouseStoragePlaceDetailSerializer(data)
        return Response(serializer.data)
