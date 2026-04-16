from decimal import Decimal

from django.db import models, transaction

from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from orders.models import ExternalReceiptItem

from .models import WarehouseLocation, WarehouseStoragePlace, WarehouseUnit
from .serializers import (
    WarehouseLocationSerializer,
    WarehouseStoragePlaceSerializer,
    WarehouseUnitSerializer,
    WarehousePendingIntakeItemSerializer,
    WarehouseAcceptPendingIntakeSerializer,
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
            queryset = queryset.filter(location_id__in=location)

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

        if receipt_item.received_quantity != int(receipt_item.received_quantity):
            raise ValidationError(
                "Неможливо прийняти без конвертації рядок з нецілою кількістю."
            )

        units_count = int(receipt_item.received_quantity)

        with transaction.atomic():
            units_to_create = []
            for _ in range(units_count):
                units_to_create.append(
                    WarehouseUnit(
                        inventory_item=order_item.vendor_item.item,
                        location=location,
                        quantity=Decimal("1.000"),
                        source_receipt_item=receipt_item,
                        source_order_item=order_item,
                    )
                )

            WarehouseUnit.objects.bulk_create(units_to_create)

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
            "created_units": units_count,
            "location_id": location.id,
            "receipt_item_id": receipt_item.id,
            "receipt_document_id": receipt_document.id,
            "sent_to_warehouse": receipt_document.sent_to_warehouse,
        })