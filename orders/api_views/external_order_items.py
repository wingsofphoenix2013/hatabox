from django.db import models, transaction
from django.db.models import Prefetch

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError

from orders.models import (
    ExternalOrder,
    ExternalOrderItem,
    ExternalReceiptItem,
)

from orders.serializers import ExternalOrderItemSerializer

from .external_orders import recalculate_order_vat_amount

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

    def perform_create(self, serializer):
        with transaction.atomic():
            order_item = serializer.save()
            recalculate_order_vat_amount(order_item.order)

    def perform_update(self, serializer):
        with transaction.atomic():
            order_item = serializer.save()
            recalculate_order_vat_amount(order_item.order)

    def perform_destroy(self, instance):
        if instance.order.status != ExternalOrder.StatusChoices.DRAFT:
            raise ValidationError(
                "Видалення рядків замовлення дозволене лише для замовлень у статусі 'Чернетка'."
            )

        order = instance.order

        with transaction.atomic():
            instance.delete()
            recalculate_order_vat_amount(order)
