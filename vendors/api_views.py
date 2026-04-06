from django.db import models
from django.db.models import Prefetch

from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import DjangoModelPermissions

from .models import Vendor, VendorItem
from .serializers import VendorSerializer, VendorItemSerializer


class VendorViewSet(ModelViewSet):
    queryset = Vendor.objects.filter(is_active=True).prefetch_related(
        Prefetch(
            "vendor_items",
            queryset=VendorItem.objects.filter(
                is_active=True,
                item__is_active=True,
            ).select_related("item__category"),
            to_attr="active_vendor_items_for_categories",
        )
    ).order_by("name", "id")
    serializer_class = VendorSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        item_category = self.request.query_params.getlist("item_category")
        if item_category:
            queryset = queryset.filter(
                vendor_items__is_active=True,
                vendor_items__item__is_active=True,
                vendor_items__item__category_id__in=item_category,
            ).distinct()

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(code__icontains=search)
                | models.Q(name__icontains=search)
                | models.Q(legal_name__icontains=search)
                | models.Q(phone__icontains=search)
                | models.Q(email__icontains=search)
            )

        return queryset


class VendorItemViewSet(ModelViewSet):
    queryset = VendorItem.objects.filter(is_active=True).select_related(
        "vendor",
        "item",
        "item__category",
        "item__unit",
        "brand",
        "country_of_origin",
    ).order_by("item__name", "vendor_sku", "id")
    serializer_class = VendorItemSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        vendor = self.request.query_params.getlist("vendor")
        if vendor:
            queryset = queryset.filter(vendor_id__in=vendor)

        inv_item = self.request.query_params.getlist("inv_item")
        if inv_item:
            queryset = queryset.filter(item_id__in=inv_item)

        brand = self.request.query_params.getlist("brand")
        if brand:
            queryset = queryset.filter(brand_id__in=brand)

        country_of_origin = self.request.query_params.getlist("country_of_origin")
        if country_of_origin:
            queryset = queryset.filter(country_of_origin_id__in=country_of_origin)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(vendor_sku__icontains=search)
                | models.Q(name__icontains=search)
                | models.Q(vendor__code__icontains=search)
                | models.Q(vendor__name__icontains=search)
                | models.Q(item__internal_code__icontains=search)
                | models.Q(item__name__icontains=search)
                | models.Q(brand__name__icontains=search)
                | models.Q(country_of_origin__name__icontains=search)
                | models.Q(country_of_origin__code__icontains=search)
            )

        return queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])