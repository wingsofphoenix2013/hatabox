from django.db import models

from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from orders.models import ExternalReceiptItem

from warehouse.services.intake_procurement import (
    accept_procurement_receipt_item_to_location,
    accept_procurement_receipt_item_with_conversion,
    bulk_accept_procurement_receipt_items_to_location,
)
from warehouse.serializers import (
    WarehousePendingIntakeItemSerializer,
    WarehouseAcceptPendingIntakeSerializer,
    WarehouseAcceptConvertedPendingIntakeSerializer,
    WarehouseBulkAcceptPendingIntakeSerializer,
    WarehousePendingIntakeStatusSerializer,
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
        warehouse_units__isnull=True,
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

        inventory_item_id = self.request.query_params.get("inventory_item_id")
        if inventory_item_id:
            queryset = queryset.filter(order_item__vendor_item__item_id=inventory_item_id)

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

    @action(detail=False, methods=["get"], url_path="status")
    def status(self, request):
        count = self.get_queryset().count()
        serializer = WarehousePendingIntakeStatusSerializer(
            {
                "count": count,
                "hasPendingIntake": count > 0,
            }
        )
        return Response(serializer.data)
        
    @action(detail=True, methods=["post"], url_path="accept-to-location")
    def accept_to_location(self, request, pk=None):
        receipt_item = self.get_object()
        serializer = WarehouseAcceptPendingIntakeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        location = serializer.validated_data["location"]

        result = accept_procurement_receipt_item_to_location(
            receipt_item=receipt_item,
            location=location,
            created_by=request.user if request.user.is_authenticated else None,
        )

        return Response(result)
        
    @action(detail=True, methods=["post"], url_path="accept-with-conversion")
    def accept_with_conversion(self, request, pk=None):
        receipt_item = self.get_object()
        serializer = WarehouseAcceptConvertedPendingIntakeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        location = serializer.validated_data["location"]
        target_quantity = serializer.validated_data["target_quantity"]
        comment = serializer.validated_data.get("comment", "")

        result = accept_procurement_receipt_item_with_conversion(
            receipt_item=receipt_item,
            location=location,
            target_quantity=target_quantity,
            comment=comment,
            created_by=request.user if request.user.is_authenticated else None,
        )

        return Response(result)
        
    @action(detail=False, methods=["post"], url_path="bulk-accept-to-location")
    def bulk_accept_to_location(self, request):
        serializer = WarehouseBulkAcceptPendingIntakeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        location = serializer.validated_data["location"]
        receipt_item_ids = serializer.validated_data["receipt_item_ids"]

        result = bulk_accept_procurement_receipt_items_to_location(
            receipt_item_ids=receipt_item_ids,
            location=location,
            created_by=request.user if request.user.is_authenticated else None,
        )

        return Response(result)