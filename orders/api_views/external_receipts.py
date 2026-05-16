from django.db import models, transaction
from django.db.models import Prefetch

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError

from orders.models import (
    ExternalOrder,
    ExternalReceiptDocument,
    ExternalReceiptItem,
)

from orders.serializers import (
    ExternalReceiptDocumentSerializer,
    ExternalReceiptItemSerializer,
)

from .external_orders import try_complete_order

class ExternalReceiptDocumentViewSet(ModelViewSet):
    queryset = ExternalReceiptDocument.objects.select_related(
        "order",
        "order__vendor",
        "created_by",
    ).prefetch_related(
        Prefetch(
            "items",
            queryset=ExternalReceiptItem.objects.select_related(
                "order_item",
                "order_item__order",
                "order_item__vendor_item",
                "order_item__vendor_item__item",
                "order_item__vendor_item__item__unit",
            ),
        )
    ).order_by("-created_at", "-id")
    serializer_class = ExternalReceiptDocumentSerializer
    permission_classes = [DjangoModelPermissions]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = self.queryset

        order = self.request.query_params.getlist("order")
        if order:
            queryset = queryset.filter(order_id__in=order)

        vendor = self.request.query_params.getlist("vendor")
        if vendor:
            queryset = queryset.filter(order__vendor_id__in=vendor)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(receipt_no__icontains=search)
                | models.Q(comment__icontains=search)
                | models.Q(order__order_no__icontains=search)
                | models.Q(order__vendor__code__icontains=search)
                | models.Q(order__vendor__name__icontains=search)
                | models.Q(created_by__username__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance

        if instance.sent_to_warehouse:
            allowed_fields = {"comment", "image", "clear_image"}
            changed_fields = set(serializer.validated_data.keys())

            if not changed_fields.issubset(allowed_fields):
                raise ValidationError(
                    "Після передачі документа приходу на склад можна змінювати лише коментар або файл."
                )

        elif instance.completed:
            allowed_fields = {"sent_to_warehouse", "comment", "image", "clear_image"}
            changed_fields = set(serializer.validated_data.keys())

            if not changed_fields.issubset(allowed_fields):
                raise ValidationError(
                    "Після завершення документа приходу можна змінювати лише прапорець передачі на склад, коментар або файл."
                )

        with transaction.atomic():
            receipt_document = serializer.save()
            try_complete_order(receipt_document.order)


class ExternalReceiptItemViewSet(ModelViewSet):
    queryset = ExternalReceiptItem.objects.select_related(
        "receipt_document",
        "receipt_document__order",
        "order_item",
        "order_item__order",
        "order_item__vendor_item",
        "order_item__vendor_item__item",
        "order_item__vendor_item__item__unit",
    ).order_by("receipt_document__receipt_no", "id")
    serializer_class = ExternalReceiptItemSerializer
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

        order_item = self.request.query_params.getlist("order_item")
        if order_item:
            queryset = queryset.filter(order_item_id__in=order_item)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(receipt_document__receipt_no__icontains=search)
                | models.Q(order_item__order__order_no__icontains=search)
                | models.Q(order_item__vendor_item__vendor_sku__icontains=search)
                | models.Q(order_item__vendor_item__name__icontains=search)
                | models.Q(order_item__vendor_item__item__internal_code__icontains=search)
                | models.Q(order_item__vendor_item__item__name__icontains=search)
            )

        return queryset
        
    def perform_create(self, serializer):
        with transaction.atomic():
            receipt_item = serializer.save()
            try_complete_order(receipt_item.order_item.order)

    def perform_update(self, serializer):
        with transaction.atomic():
            receipt_item = serializer.save()
            try_complete_order(receipt_item.order_item.order)

    def perform_destroy(self, instance):
        if instance.receipt_document.completed:
            raise ValidationError(
                "Неможливо видаляти рядки приходу після завершення документа приходу."
            )

        order = instance.order_item.order

        with transaction.atomic():
            instance.delete()
            try_complete_order(order)
