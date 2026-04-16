from django.db import models

from orders.models import ExternalReceiptItem

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import WarehouseLocation, WarehouseStoragePlace, WarehouseUnit
from .serializers import (
    WarehouseLocationSerializer,
    WarehouseStoragePlaceSerializer,
    WarehouseUnitSerializer,
    WarehousePendingIntakeItemSerializer,
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