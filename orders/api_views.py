from django.db import models

from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import DjangoModelPermissions

from .models import ExternalOrder, ExternalOrderItem
from .serializers import ExternalOrderSerializer, ExternalOrderItemSerializer


class ExternalOrderViewSet(ModelViewSet):
    queryset = ExternalOrder.objects.filter(is_active=True).select_related(
        "vendor",
        "status",
        "payment_status",
        "created_by",
    ).prefetch_related(
        "items__vendor_item__vendor",
        "items__vendor_item__item__category",
        "items__vendor_item__item__unit",
        "items__vendor_item__brand",
        "items__vendor_item__country_of_origin",
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
            queryset = queryset.filter(status_id__in=status)

        payment_status = self.request.query_params.getlist("payment_status")
        if payment_status:
            queryset = queryset.filter(payment_status_id__in=payment_status)

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
                | models.Q(status__code__icontains=search)
                | models.Q(status__name__icontains=search)
                | models.Q(payment_status__code__icontains=search)
                | models.Q(payment_status__name__icontains=search)
                | models.Q(created_by__username__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ExternalOrderItemViewSet(ModelViewSet):
    queryset = ExternalOrderItem.objects.filter(is_active=True).select_related(
        "order",
        "order__vendor",
        "vendor_item",
        "vendor_item__vendor",
        "vendor_item__item",
        "vendor_item__item__category",
        "vendor_item__item__unit",
        "vendor_item__brand",
        "vendor_item__country_of_origin",
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