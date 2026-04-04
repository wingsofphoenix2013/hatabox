from django.db import models

from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import (
    Brand,
    Country,
    ExternalOrderStatus,
    ExternalOrderPaymentStatus,
    TaxType,
)
from .serializers import (
    BrandSerializer,
    CountrySerializer,
    ExternalOrderStatusSerializer,
    ExternalOrderPaymentStatusSerializer,
    TaxTypeSerializer,
)


class BrandViewSet(ReadOnlyModelViewSet):
    queryset = Brand.objects.filter(is_active=True).order_by("name", "id")
    serializer_class = BrandSerializer

    def get_queryset(self):
        queryset = self.queryset

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
            )

        return queryset


class CountryViewSet(ReadOnlyModelViewSet):
    queryset = Country.objects.filter(is_active=True).order_by("name", "id")
    serializer_class = CountrySerializer

    def get_queryset(self):
        queryset = self.queryset

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(code__icontains=search)
            )

        return queryset


class ExternalOrderStatusViewSet(ReadOnlyModelViewSet):
    queryset = ExternalOrderStatus.objects.filter(is_active=True)
    serializer_class = ExternalOrderStatusSerializer

    def get_queryset(self):
        queryset = self.queryset

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(code__icontains=search)
                | models.Q(name__icontains=search)
            )

        return queryset


class ExternalOrderPaymentStatusViewSet(ReadOnlyModelViewSet):
    queryset = ExternalOrderPaymentStatus.objects.filter(is_active=True)
    serializer_class = ExternalOrderPaymentStatusSerializer

    def get_queryset(self):
        queryset = self.queryset

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(code__icontains=search)
                | models.Q(name__icontains=search)
            )

        return queryset


class TaxTypeViewSet(ReadOnlyModelViewSet):
    queryset = TaxType.objects.filter(is_active=True)
    serializer_class = TaxTypeSerializer

    def get_queryset(self):
        queryset = self.queryset

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(code__icontains=search)
                | models.Q(name__icontains=search)
            )

        return queryset