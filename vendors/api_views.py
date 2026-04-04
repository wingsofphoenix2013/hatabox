from django.db import models

from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import DjangoModelPermissions

from .models import Vendor, VendorItem
from .serializers import VendorSerializer, VendorItemSerializer


class VendorViewSet(ModelViewSet):
    queryset = Vendor.objects.filter(is_active=True)
    serializer_class = VendorSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

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
    )
    serializer_class = VendorItemSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        vendor = self.request.query_params.getlist("vendor")
        if vendor:
            queryset = queryset.filter(vendor_id__in=vendor)

        item = self.request.query_params.getlist("item")
        if item:
            queryset = queryset.filter(item_id__in=item)

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