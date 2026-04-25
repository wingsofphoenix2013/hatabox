from decimal import Decimal

from django.db import models, transaction

from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from orders.models import ExternalReceiptItem
from warehouse.models import (
    WarehouseReceiptItemConversion,
    WarehouseUnit,
    WarehouseUnitEvent,
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
        
    @action(detail=True, methods=["post"], url_path="accept-with-conversion")
    def accept_with_conversion(self, request, pk=None):
        receipt_item = self.get_object()
        serializer = WarehouseAcceptConvertedPendingIntakeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        location = serializer.validated_data["location"]
        target_quantity = serializer.validated_data["target_quantity"]
        comment = serializer.validated_data.get("comment", "")

        receipt_document = receipt_item.receipt_document
        order_item = receipt_item.order_item

        if not receipt_document.completed:
            raise ValidationError("Документ приходу повинен бути завершеним.")

        if receipt_document.sent_to_warehouse:
            raise ValidationError("Документ приходу вже передано на склад.")

        if not order_item.requires_unit_conversion:
            raise ValidationError(
                "Цей рядок не потребує конвертації одиниць."
            )

        existing_units = WarehouseUnit.objects.filter(
            source_receipt_item=receipt_item,
            is_active=True,
        )
        if existing_units.exists():
            raise ValidationError("Цей рядок приходу вже оброблено складом.")

        with transaction.atomic():
            conversion = WarehouseReceiptItemConversion.objects.create(
                receipt_item=receipt_item,
                source_quantity=receipt_item.received_quantity,
                target_quantity=target_quantity,
                comment=comment,
                created_by=request.user if request.user.is_authenticated else None,
            )

            whole_units = int(target_quantity)
            fractional_part = target_quantity - Decimal(whole_units)

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
                    operation_type=WarehouseUnitEvent.OperationType.CONVERTED_INTAKE,
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
            "conversion_id": conversion.id,
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
