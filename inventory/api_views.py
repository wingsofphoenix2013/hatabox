from django.db import models

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import (
    InvUnit,
    InvItemCategory,
    InvItem,
    ProductFamily,
    ProductFamilyLibrary,
)
from .serializers import (
    InvUnitSerializer,
    InvItemCategorySerializer,
    InvItemSerializer,
    ProductFamilySerializer,
    ProductFamilyLibrarySerializer,
)


class InvUnitViewSet(ReadOnlyModelViewSet):
    queryset = InvUnit.objects.filter(is_active=True)
    serializer_class = InvUnitSerializer


class InvItemCategoryViewSet(ReadOnlyModelViewSet):
    queryset = InvItemCategory.objects.filter(is_active=True)
    serializer_class = InvItemCategorySerializer


class InvItemViewSet(ModelViewSet):
    queryset = InvItem.objects.filter(is_active=True)
    serializer_class = InvItemSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset.select_related("category", "unit")

        category = self.request.query_params.getlist("category")
        if category:
            queryset = queryset.filter(category_id__in=category)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(internal_code__icontains=search)
            )

        return queryset


class ProductFamilyViewSet(ModelViewSet):
    queryset = ProductFamily.objects.filter(is_active=True)
    serializer_class = ProductFamilySerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset.prefetch_related("library_items")

        developer = self.request.query_params.getlist("developer")
        if developer:
            queryset = queryset.filter(developer__in=developer)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(code__icontains=search)
                | models.Q(name__icontains=search)
                | models.Q(description__icontains=search)
            )

        return queryset


class ProductFamilyLibraryViewSet(ModelViewSet):
    queryset = ProductFamilyLibrary.objects.filter(is_active=True).select_related("product_family")
    serializer_class = ProductFamilyLibrarySerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        product_family = self.request.query_params.getlist("product_family")
        if product_family:
            queryset = queryset.filter(product_family_id__in=product_family)

        attachment_type = self.request.query_params.getlist("attachment_type")
        if attachment_type:
            queryset = queryset.filter(attachment_type__in=attachment_type)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(description__icontains=search)
                | models.Q(product_family__code__icontains=search)
                | models.Q(product_family__name__icontains=search)
            )

        return queryset