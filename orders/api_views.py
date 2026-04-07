from django.db import models
from django.db.models import Prefetch

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError

from .models import (
    ExternalOrder,
    ExternalOrderItem,
    ExternalPaymentDocument,
    ExternalReceiptDocument,
    ExternalReceiptItem,
)
from .serializers import (
    ExternalOrderSerializer,
    ExternalOrderItemSerializer,
    ExternalPaymentDocumentSerializer,
    ExternalReceiptDocumentSerializer,
    ExternalReceiptItemSerializer,
)


class ExternalOrderViewSet(ModelViewSet):
    queryset = ExternalOrder.objects.select_related(
        "vendor",
        "created_by",
    ).prefetch_related(
        Prefetch(
            "items",
            queryset=ExternalOrderItem.objects.select_related(
                "vendor_item",
                "vendor_item__vendor",
                "vendor_item__item",
                "vendor_item__item__category",
                "vendor_item__item__unit",
                "vendor_item__brand",
                "vendor_item__country_of_origin",
            ).prefetch_related(
                Prefetch(
                    "receipt_items",
                    queryset=ExternalReceiptItem.objects.select_related("receipt_document"),
                    to_attr="prefetched_receipt_items",
                )
            ),
            to_attr="prefetched_items",
        ),
        Prefetch(
            "payment_documents",
            queryset=ExternalPaymentDocument.objects.select_related("created_by"),
            to_attr="prefetched_payment_documents",
        ),
    ).order_by("-created_at", "-id")
    serializer_class = ExternalOrderSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        vendor = self.request.query_params.getlist("vendor")
        if vendor:
            queryset = queryset.filter(vendor_id__in=vendor)

        status = self.request.query_params.getlist("status")
        if status:
            queryset = queryset.filter(status__in=status)

        created_by = self.request.query_params.getlist("created_by")
        if created_by:
            queryset = queryset.filter(created_by_id__in=created_by)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(order_no__icontains=search)
                | models.Q(comment__icontains=search)
                | models.Q(vendor__code__icontains=search)
                | models.Q(vendor__name__icontains=search)
                | models.Q(created_by__username__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ExternalOrderItemViewSet(ModelViewSet):
    queryset = ExternalOrderItem.objects.select_related(
        "order",
        "order__vendor",
        "vendor_item",
        "vendor_item__vendor",
        "vendor_item__item",
        "vendor_item__item__category",
        "vendor_item__item__unit",
        "vendor_item__brand",
        "vendor_item__country_of_origin",
    ).prefetch_related(
        Prefetch(
            "receipt_items",
            queryset=ExternalReceiptItem.objects.select_related("receipt_document"),
            to_attr="prefetched_receipt_items",
        )
    ).order_by("order__order_no", "id")
    serializer_class = ExternalOrderItemSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        order = self.request.query_params.getlist("order")
        if order:
            queryset = queryset.filter(order_id__in=order)

        vendor = self.request.query_params.getlist("vendor")
        if vendor:
            queryset = queryset.filter(order__vendor_id__in=vendor)

        vendor_item = self.request.query_params.getlist("vendor_item")
        if vendor_item:
            queryset = queryset.filter(vendor_item_id__in=vendor_item)

        inv_item = self.request.query_params.getlist("inv_item")
        if inv_item:
            queryset = queryset.filter(vendor_item__item_id__in=inv_item)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(order__order_no__icontains=search)
                | models.Q(vendor_item__vendor_sku__icontains=search)
                | models.Q(vendor_item__name__icontains=search)
                | models.Q(vendor_item__vendor__code__icontains=search)
                | models.Q(vendor_item__vendor__name__icontains=search)
                | models.Q(vendor_item__item__internal_code__icontains=search)
                | models.Q(vendor_item__item__name__icontains=search)
                | models.Q(vendor_item__brand__name__icontains=search)
                | models.Q(vendor_item__country_of_origin__name__icontains=search)
                | models.Q(vendor_item__country_of_origin__code__icontains=search)
            )

        return queryset

    def perform_destroy(self, instance):
        if instance.order.status != ExternalOrder.StatusChoices.DRAFT:
            raise ValidationError(
                "Видалення рядків замовлення дозволене лише для замовлень у статусі 'Чернетка'."
            )
        instance.delete()


class ExternalPaymentDocumentViewSet(ModelViewSet):
    queryset = ExternalPaymentDocument.objects.select_related(
        "order",
        "order__vendor",
        "created_by",
    ).order_by("-created_at", "-id")
    serializer_class = ExternalPaymentDocumentSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        order = self.request.query_params.getlist("order")
        if order:
            queryset = queryset.filter(order_id__in=order)

        vendor = self.request.query_params.getlist("vendor")
        if vendor:
            queryset = queryset.filter(order__vendor_id__in=vendor)

        status = self.request.query_params.getlist("status")
        if status:
            queryset = queryset.filter(status__in=status)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(payment_no__icontains=search)
                | models.Q(comment__icontains=search)
                | models.Q(order__order_no__icontains=search)
                | models.Q(order__vendor__code__icontains=search)
                | models.Q(order__vendor__name__icontains=search)
                | models.Q(created_by__username__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


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