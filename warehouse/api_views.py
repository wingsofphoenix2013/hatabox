from collections import OrderedDict
from decimal import Decimal
import traceback

from django.db import models, transaction
from django.db.models import Case, CharField, F, Value, When
from django.db.models.functions import Concat

from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from orders.models import ExternalReceiptItem

from .models import (
    WarehouseLocation,
    WarehouseStoragePlace,
    WarehouseUnit,
    WarehouseUnitEvent,
)
from .services.movement import plan_move, execute_move, execute_bulk_move
from .services.stock_overview import build_stock_overview
from .serializers import (
    WarehouseLocationSerializer,
    WarehouseStoragePlaceSerializer,
    WarehouseUnitSerializer,
    WarehousePendingIntakeItemSerializer,
    WarehouseAcceptPendingIntakeSerializer,
    WarehouseBulkAcceptPendingIntakeSerializer,
    WarehouseDebugPlanMoveSerializer,
    WarehouseDebugExecuteMoveSerializer,
    WarehouseDebugExecuteBulkMoveSerializer,
    WarehouseMoveSerializer,
    WarehouseBulkMoveSerializer,
    WarehouseStockOverviewRowSerializer,
)


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
                | models.Q(qr_code__icontains=search)
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

    def _place_type_priority(self, place_type):
        priority_map = {
            WarehouseStoragePlace.PlaceType.CONTAINER: 0,
            WarehouseStoragePlace.PlaceType.RACK: 1,
            WarehouseStoragePlace.PlaceType.BOX: 2,
        }
        return priority_map.get(place_type, 99)

    def _sort_storage_places_hierarchically(self, queryset):
        places = list(queryset)

        locations = OrderedDict()
        children_map = {}

        for place in places:
            locations[place.location_id] = place.location
            children_map.setdefault(place.parent_id, []).append(place)

        for parent_id in children_map:
            children_map[parent_id].sort(
                key=lambda x: (
                    self._place_type_priority(x.place_type),
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
                    self._place_type_priority(x.place_type),
                    x.code,
                    x.id,
                )
            )

            for root in root_places:
                ordered.append(root)
                walk(root.id)

        return ordered

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        ordered_places = self._sort_storage_places_hierarchically(queryset)

        page = self.paginate_queryset(ordered_places)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(ordered_places, many=True)
        return Response(serializer.data)


class WarehouseUnitViewSet(ModelViewSet):
    queryset = WarehouseUnit.objects.select_related(
        "inventory_item",
        "inventory_item__unit",
        "location",
        "storage_place",
        "storage_place__location",
        "source_receipt_item",
        "source_order_item",
        "source_order_item__order",
        "source_order_item__vendor_item",
    ).order_by("inventory_item__name", "id")

    serializer_class = WarehouseUnitSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        inventory_item = self.request.query_params.getlist("inventory_item")
        if inventory_item:
            queryset = queryset.filter(inventory_item_id__in=inventory_item)

        location = self.request.query_params.getlist("location")
        if location:
            queryset = queryset.filter(
                models.Q(location_id__in=location)
                | models.Q(storage_place__location_id__in=location)
            )

        storage_place = self.request.query_params.getlist("storage_place")
        if storage_place:
            queryset = queryset.filter(storage_place_id__in=storage_place)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(inventory_item__internal_code__icontains=search)
                | models.Q(inventory_item__name__icontains=search)
                | models.Q(source_order_item__order__order_no__icontains=search)
                | models.Q(source_order_item__vendor_item__name__icontains=search)
            )

        return queryset

    @action(detail=False, methods=["post"], url_path="move")
    def move(self, request):
        serializer = WarehouseMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        inventory_item = serializer.validated_data["inventory_item"]
        quantity = serializer.validated_data["quantity"]
        target_location = serializer.validated_data.get("target_location")
        target_storage_place = serializer.validated_data.get("target_storage_place")

        execution_result = execute_move(
            inventory_item=inventory_item,
            quantity=quantity,
            target_location=target_location,
            target_storage_place=target_storage_place,
            created_by=request.user if request.user.is_authenticated else None,
        )

        return Response({
            "inventory_item_id": execution_result.move_plan.inventory_item_id,
            "requested_quantity": str(execution_result.move_plan.requested_quantity),
            "requires_split": execution_result.move_plan.requires_split,
            "destination": {
                "location_id": target_location.id if target_location is not None else None,
                "storage_place_id": (
                    target_storage_place.id
                    if target_storage_place is not None
                    else None
                ),
            },
            "moved_units": [
                {
                    "id": unit.id,
                    "quantity": str(unit.quantity),
                    "location_id": unit.location_id,
                    "storage_place_id": unit.storage_place_id,
                }
                for unit in execution_result.moved_units
            ],
            "created_unit": (
                {
                    "id": execution_result.created_unit.id,
                    "quantity": str(execution_result.created_unit.quantity),
                    "location_id": execution_result.created_unit.location_id,
                    "storage_place_id": execution_result.created_unit.storage_place_id,
                }
                if execution_result.created_unit is not None
                else None
            ),
            "split_source_unit": (
                {
                    "id": execution_result.split_source_unit.id,
                    "quantity": str(execution_result.split_source_unit.quantity),
                    "location_id": execution_result.split_source_unit.location_id,
                    "storage_place_id": execution_result.split_source_unit.storage_place_id,
                }
                if execution_result.split_source_unit is not None
                else None
            ),
        })

    @action(detail=False, methods=["post"], url_path="bulk-move")
    def bulk_move(self, request):
        serializer = WarehouseBulkMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        unit_ids = serializer.validated_data["unit_ids"]
        target_location = serializer.validated_data.get("target_location")
        target_storage_place = serializer.validated_data.get("target_storage_place")

        execution_result = execute_bulk_move(
            unit_ids=unit_ids,
            target_location=target_location,
            target_storage_place=target_storage_place,
            created_by=request.user if request.user.is_authenticated else None,
        )

        return Response({
            "destination": {
                "location_id": target_location.id if target_location is not None else None,
                "storage_place_id": (
                    target_storage_place.id
                    if target_storage_place is not None
                    else None
                ),
            },
            "moved_units": [
                {
                    "id": unit.id,
                    "quantity": str(unit.quantity),
                    "location_id": unit.location_id,
                    "storage_place_id": unit.storage_place_id,
                }
                for unit in execution_result.moved_units
            ],
        })

    @action(detail=False, methods=["get", "post"], url_path="debug-plan-move")
    def debug_plan_move(self, request):
        input_data = request.query_params if request.method == "GET" else request.data

        serializer = WarehouseDebugPlanMoveSerializer(data=input_data)
        serializer.is_valid(raise_exception=True)

        inventory_item = serializer.validated_data["inventory_item"]
        quantity = serializer.validated_data["quantity"]

        move_plan = plan_move(
            inventory_item=inventory_item,
            quantity=quantity,
        )

        return Response({
            "inventory_item_id": move_plan.inventory_item_id,
            "requested_quantity": str(move_plan.requested_quantity),
            "requires_split": move_plan.requires_split,
            "full_units": [
                {
                    "id": unit.id,
                    "quantity": str(unit.quantity),
                    "location_id": unit.location_id,
                    "storage_place_id": unit.storage_place_id,
                }
                for unit in move_plan.full_units
            ],
            "split_source_unit": (
                {
                    "id": move_plan.split_source_unit.id,
                    "quantity": str(move_plan.split_source_unit.quantity),
                    "location_id": move_plan.split_source_unit.location_id,
                    "storage_place_id": move_plan.split_source_unit.storage_place_id,
                }
                if move_plan.split_source_unit is not None
                else None
            ),
            "split_move_quantity": (
                str(move_plan.split_move_quantity)
                if move_plan.split_move_quantity is not None
                else None
            ),
            "split_remainder_quantity": (
                str(move_plan.split_remainder_quantity)
                if move_plan.split_remainder_quantity is not None
                else None
            ),
        })

    @action(detail=False, methods=["get", "post"], url_path="debug-execute-move")
    def debug_execute_move(self, request):
        try:
            input_data = request.query_params if request.method == "GET" else request.data

            serializer = WarehouseDebugExecuteMoveSerializer(data=input_data)
            serializer.is_valid(raise_exception=True)

            inventory_item = serializer.validated_data["inventory_item"]
            quantity = serializer.validated_data["quantity"]
            target_location = serializer.validated_data.get("target_location")
            target_storage_place = serializer.validated_data.get("target_storage_place")

            execution_result = execute_move(
                inventory_item=inventory_item,
                quantity=quantity,
                target_location=target_location,
                target_storage_place=target_storage_place,
                created_by=request.user if request.user.is_authenticated else None,
            )

            return Response({
                "inventory_item_id": execution_result.move_plan.inventory_item_id,
                "requested_quantity": str(execution_result.move_plan.requested_quantity),
                "requires_split": execution_result.move_plan.requires_split,
                "destination": {
                    "location_id": target_location.id if target_location is not None else None,
                    "storage_place_id": (
                        target_storage_place.id
                        if target_storage_place is not None
                        else None
                    ),
                },
                "moved_units": [
                    {
                        "id": unit.id,
                        "quantity": str(unit.quantity),
                        "location_id": unit.location_id,
                        "storage_place_id": unit.storage_place_id,
                    }
                    for unit in execution_result.moved_units
                ],
                "created_unit": (
                    {
                        "id": execution_result.created_unit.id,
                        "quantity": str(execution_result.created_unit.quantity),
                        "location_id": execution_result.created_unit.location_id,
                        "storage_place_id": execution_result.created_unit.storage_place_id,
                    }
                    if execution_result.created_unit is not None
                    else None
                ),
                "split_source_unit": (
                    {
                        "id": execution_result.split_source_unit.id,
                        "quantity": str(execution_result.split_source_unit.quantity),
                        "location_id": execution_result.split_source_unit.location_id,
                        "storage_place_id": execution_result.split_source_unit.storage_place_id,
                    }
                    if execution_result.split_source_unit is not None
                    else None
                ),
            })
        except Exception as exc:
            return Response(
                {
                    "error_type": exc.__class__.__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
                status=500,
            )

    @action(detail=False, methods=["get", "post"], url_path="debug-execute-bulk-move")
    def debug_execute_bulk_move(self, request):
        try:
            input_data = request.query_params if request.method == "GET" else request.data

            serializer = WarehouseDebugExecuteBulkMoveSerializer(data=input_data)
            serializer.is_valid(raise_exception=True)

            unit_ids = serializer.validated_data["unit_ids"]
            target_location = serializer.validated_data.get("target_location")
            target_storage_place = serializer.validated_data.get("target_storage_place")

            execution_result = execute_bulk_move(
                unit_ids=unit_ids,
                target_location=target_location,
                target_storage_place=target_storage_place,
                created_by=request.user if request.user.is_authenticated else None,
            )

            return Response({
                "destination": {
                    "location_id": target_location.id if target_location is not None else None,
                    "storage_place_id": (
                        target_storage_place.id
                        if target_storage_place is not None
                        else None
                    ),
                },
                "moved_units": [
                    {
                        "id": unit.id,
                        "quantity": str(unit.quantity),
                        "location_id": unit.location_id,
                        "storage_place_id": unit.storage_place_id,
                    }
                    for unit in execution_result.moved_units
                ],
            })
        except Exception as exc:
            return Response(
                {
                    "error_type": exc.__class__.__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
                status=500,
            )


class WarehousePendingIntakeItemViewSet(ReadOnlyModelViewSet):
    queryset = ExternalReceiptItem.objects.select_related(
        "receipt_document",
        "receipt_document__order",
        "receipt_document__order__vendor",
        "order_item",
        "order_item__order",
        "order_item__order__vendor",
        "order_item__vendor_item",
        "order_item__vendor_item__item",
        "order_item__vendor_item__item__unit",
    ).filter(
        receipt_document__completed=True,
        receipt_document__sent_to_warehouse=False,
    ).exclude(
        warehouse_units__is_active=True,
    ).order_by("receipt_document__receipt_date", "receipt_document__id", "id")

    serializer_class = WarehousePendingIntakeItemSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        receipt_document = self.request.query_params.getlist("receipt_document")
        if receipt_document:
            queryset = queryset.filter(receipt_document_id__in=receipt_document)

        order = self.request.query_params.getlist("order")
        if order:
            queryset = queryset.filter(order_item__order_id__in=order)

        vendor = self.request.query_params.getlist("vendor")
        if vendor:
            queryset = queryset.filter(order_item__order__vendor_id__in=vendor)

        inventory_item = self.request.query_params.getlist("inventory_item")
        if inventory_item:
            queryset = queryset.filter(order_item__vendor_item__item_id__in=inventory_item)

        requires_unit_conversion = self.request.query_params.get("requires_unit_conversion")
        if requires_unit_conversion is not None:
            queryset = queryset.filter(
                order_item__requires_unit_conversion=requires_unit_conversion.lower() == "true"
            )

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(receipt_document__receipt_no__icontains=search)
                | models.Q(order_item__order__order_no__icontains=search)
                | models.Q(order_item__order__vendor__code__icontains=search)
                | models.Q(order_item__order__vendor__name__icontains=search)
                | models.Q(order_item__vendor_item__name__icontains=search)
                | models.Q(order_item__vendor_item__vendor_sku__icontains=search)
                | models.Q(order_item__vendor_item__item__internal_code__icontains=search)
                | models.Q(order_item__vendor_item__item__name__icontains=search)
            )

        return queryset

    @action(detail=True, methods=["post"], url_path="accept-to-location")
    def accept_to_location(self, request, pk=None):
        receipt_item = self.get_object()
        serializer = WarehouseAcceptPendingIntakeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        location = serializer.validated_data["location"]
        receipt_document = receipt_item.receipt_document
        order_item = receipt_item.order_item

        if not receipt_document.completed:
            raise ValidationError("Документ приходу повинен бути завершеним.")

        if receipt_document.sent_to_warehouse:
            raise ValidationError("Документ приходу вже передано на склад.")

        if order_item.requires_unit_conversion:
            raise ValidationError(
                "Для цього рядка приходу потрібна окрема операція конвертації одиниць."
            )

        existing_units = WarehouseUnit.objects.filter(
            source_receipt_item=receipt_item,
            is_active=True,
        )
        if existing_units.exists():
            raise ValidationError("Цей рядок приходу вже оброблено складом.")

        whole_units = int(receipt_item.received_quantity)
        fractional_part = receipt_item.received_quantity - Decimal(whole_units)

        with transaction.atomic():
            units_to_create = []

            for _ in range(whole_units):
                units_to_create.append(
                    WarehouseUnit(
                        inventory_item=order_item.vendor_item.item,
                        location=location,
                        quantity=Decimal("1.000"),
                        source_receipt_item=receipt_item,
                        source_order_item=order_item,
                    )
                )

            if fractional_part > 0:
                units_to_create.append(
                    WarehouseUnit(
                        inventory_item=order_item.vendor_item.item,
                        location=location,
                        quantity=fractional_part,
                        source_receipt_item=receipt_item,
                        source_order_item=order_item,
                    )
                )

            created_units = WarehouseUnit.objects.bulk_create(units_to_create)

            WarehouseUnitEvent.objects.bulk_create([
                WarehouseUnitEvent(
                    operation_type=WarehouseUnitEvent.OperationType.INTAKE,
                    source_unit=None,
                    result_unit=unit,
                    quantity=unit.quantity,
                    from_location=None,
                    from_storage_place=None,
                    to_location=unit.location,
                    to_storage_place=unit.storage_place,
                    created_by=request.user if request.user.is_authenticated else None,
                )
                for unit in created_units
            ])

            remaining_items = ExternalReceiptItem.objects.filter(
                receipt_document=receipt_document,
            ).exclude(
                warehouse_units__is_active=True,
            ).distinct()

            if not remaining_items.exists():
                receipt_document.sent_to_warehouse = True
                receipt_document.save(update_fields=["sent_to_warehouse"])

        return Response({
            "status": "ok",
            "created_units": len(units_to_create),
            "location_id": location.id,
            "receipt_item_id": receipt_item.id,
            "receipt_document_id": receipt_document.id,
            "sent_to_warehouse": receipt_document.sent_to_warehouse,
        })
        
    @action(detail=False, methods=["post"], url_path="bulk-accept-to-location")
    def bulk_accept_to_location(self, request):
        serializer = WarehouseBulkAcceptPendingIntakeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        location = serializer.validated_data["location"]
        receipt_item_ids = serializer.validated_data["receipt_item_ids"]

        receipt_items = list(
            ExternalReceiptItem.objects.select_related(
                "receipt_document",
                "order_item",
                "order_item__vendor_item",
                "order_item__vendor_item__item",
            ).filter(
                id__in=receipt_item_ids,
            )
        )

        found_ids = {item.id for item in receipt_items}
        missing_ids = [item_id for item_id in receipt_item_ids if item_id not in found_ids]
        if missing_ids:
            raise ValidationError({
                "receipt_item_ids": (
                    f"Не знайдено рядки приходу з id: {missing_ids}"
                )
            })

        existing_units = set(
            WarehouseUnit.objects.filter(
                source_receipt_item_id__in=receipt_item_ids,
                is_active=True,
            ).values_list("source_receipt_item_id", flat=True)
        )
        if existing_units:
            raise ValidationError({
                "receipt_item_ids": (
                    f"Деякі рядки приходу вже оброблено складом: {sorted(existing_units)}"
                )
            })

        units_to_create = []
        affected_receipt_document_ids = set()

        for receipt_item in receipt_items:
            receipt_document = receipt_item.receipt_document
            order_item = receipt_item.order_item

            if not receipt_document.completed:
                raise ValidationError(
                    f"Документ приходу для рядка {receipt_item.id} повинен бути завершеним."
                )

            if receipt_document.sent_to_warehouse:
                raise ValidationError(
                    f"Документ приходу для рядка {receipt_item.id} вже передано на склад."
                )

            if order_item.requires_unit_conversion:
                raise ValidationError(
                    f"Рядок приходу {receipt_item.id} потребує окремої операції конвертації одиниць."
                )

            whole_units = int(receipt_item.received_quantity)
            fractional_part = receipt_item.received_quantity - Decimal(whole_units)
            affected_receipt_document_ids.add(receipt_document.id)

            for _ in range(whole_units):
                units_to_create.append(
                    WarehouseUnit(
                        inventory_item=order_item.vendor_item.item,
                        location=location,
                        quantity=Decimal("1.000"),
                        source_receipt_item=receipt_item,
                        source_order_item=order_item,
                    )
                )

            if fractional_part > 0:
                units_to_create.append(
                    WarehouseUnit(
                        inventory_item=order_item.vendor_item.item,
                        location=location,
                        quantity=fractional_part,
                        source_receipt_item=receipt_item,
                        source_order_item=order_item,
                    )
                )
                
        with transaction.atomic():
            created_units = WarehouseUnit.objects.bulk_create(units_to_create)

            WarehouseUnitEvent.objects.bulk_create([
                WarehouseUnitEvent(
                    operation_type=WarehouseUnitEvent.OperationType.INTAKE,
                    source_unit=None,
                    result_unit=unit,
                    quantity=unit.quantity,
                    from_location=None,
                    from_storage_place=None,
                    to_location=unit.location,
                    to_storage_place=unit.storage_place,
                    created_by=request.user if request.user.is_authenticated else None,
                )
                for unit in created_units
            ])

            for receipt_document_id in affected_receipt_document_ids:
                remaining_items = ExternalReceiptItem.objects.filter(
                    receipt_document_id=receipt_document_id,
                ).exclude(
                    warehouse_units__is_active=True,
                ).distinct()

                if not remaining_items.exists():
                    ExternalReceiptItem.objects.filter(
                        receipt_document_id=receipt_document_id
                    ).first().receipt_document.__class__.objects.filter(
                        id=receipt_document_id
                    ).update(sent_to_warehouse=True)

        return Response({
            "status": "ok",
            "processed_receipt_item_ids": receipt_item_ids,
            "created_units": len(units_to_create),
            "location_id": location.id,
        })
        
class WarehouseStockOverviewViewSet(ReadOnlyModelViewSet):
    serializer_class = WarehouseStockOverviewRowSerializer
    permission_classes = [DjangoModelPermissions]

    def list(self, request, *args, **kwargs):
        search = request.query_params.get("search")

        category_ids = request.query_params.getlist("category")
        location_ids = request.query_params.getlist("location")

        has_stock = request.query_params.get("has_stock")
        has_pending_intake = request.query_params.get("has_pending_intake")
        has_incoming = request.query_params.get("has_incoming")
        has_unconverted_expectation = request.query_params.get("has_unconverted_expectation")

        def parse_bool(value):
            if value is None:
                return None
            return value.lower() == "true"

        try:
            rows = build_stock_overview(
                search=search,
                category_ids=category_ids,
                location_ids=location_ids,
                has_stock=parse_bool(has_stock),
                has_pending_intake=parse_bool(has_pending_intake),
                has_incoming=parse_bool(has_incoming),
                has_unconverted_expectation=parse_bool(has_unconverted_expectation),
            )

            page = self.paginate_queryset(rows)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(rows, many=True)
            return Response(serializer.data)

        except Exception as exc:
            return Response(
                {
                    "stage": "build_stock_overview",
                    "error_type": exc.__class__.__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                    "query_params": {
                        "search": search,
                        "category": category_ids,
                        "location": location_ids,
                        "has_stock": has_stock,
                        "has_pending_intake": has_pending_intake,
                        "has_incoming": has_incoming,
                        "has_unconverted_expectation": has_unconverted_expectation,
                    },
                },
                status=500,
            )