from django.db import models

from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import ModelViewSet

from .models import (
    Organization,
    CommercialOrganization,
    MilitaryOrganization,
    CharityOrganization,
)
from .serializers import (
    OrganizationListSerializer,
    OrganizationSerializer,
    CommercialOrganizationSerializer,
    MilitaryOrganizationSerializer,
    CharityOrganizationSerializer,
)


class OrganizationViewSet(ModelViewSet):
    queryset = Organization.objects.order_by("name", "id")
    serializer_class = OrganizationSerializer
    permission_classes = [DjangoModelPermissions]
    pagination_class = None

    def get_serializer_class(self):
        if self.action == "list":
            return OrganizationSerializer
        return OrganizationSerializer

    def get_pagination_class(self):
        paginated = self.request.query_params.get("paginated")
        if paginated and paginated.lower() == "true":
            return PageNumberPagination
        return None

    @property
    def paginator(self):
        if not hasattr(self, "_paginator"):
            pagination_class = self.get_pagination_class()
            self._paginator = pagination_class() if pagination_class else None
        return self._paginator

    def get_queryset(self):
        queryset = self.queryset

        org_type = self.request.query_params.getlist("type")
        if org_type:
            queryset = queryset.filter(type__in=org_type)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=(is_active.lower() == "true"))

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(legal_name__icontains=search)
                | models.Q(edrpou__icontains=search)
            )

        return queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class CommercialOrganizationViewSet(ModelViewSet):
    queryset = CommercialOrganization.objects.select_related(
        "organization",
        "tax_type",
    ).order_by("organization__name", "id")
    serializer_class = CommercialOrganizationSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        organization = self.request.query_params.getlist("organization")
        if organization:
            queryset = queryset.filter(organization_id__in=organization)

        tax_type = self.request.query_params.getlist("tax_type")
        if tax_type:
            queryset = queryset.filter(tax_type_id__in=tax_type)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(organization__name__icontains=search)
                | models.Q(organization__legal_name__icontains=search)
                | models.Q(organization__edrpou__icontains=search)
                | models.Q(ipn__icontains=search)
                | models.Q(legal_address__icontains=search)
                | models.Q(tax_type__name__icontains=search)
            )

        return queryset


class MilitaryOrganizationViewSet(ModelViewSet):
    queryset = MilitaryOrganization.objects.select_related(
        "organization",
    ).order_by("organization__name", "id")
    serializer_class = MilitaryOrganizationSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        organization = self.request.query_params.getlist("organization")
        if organization:
            queryset = queryset.filter(organization_id__in=organization)

        military_type = self.request.query_params.getlist("military_type")
        if military_type:
            queryset = queryset.filter(military_type__in=military_type)

        military_branch = self.request.query_params.getlist("military_branch")
        if military_branch:
            queryset = queryset.filter(military_branch__in=military_branch)

        military_corps = self.request.query_params.getlist("military_corps")
        if military_corps:
            queryset = queryset.filter(military_corps__in=military_corps)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(organization__name__icontains=search)
                | models.Q(organization__legal_name__icontains=search)
                | models.Q(organization__edrpou__icontains=search)
                | models.Q(a_code__icontains=search)
            )

        return queryset


class CharityOrganizationViewSet(ModelViewSet):
    queryset = CharityOrganization.objects.select_related(
        "organization",
    ).order_by("organization__name", "id")
    serializer_class = CharityOrganizationSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        organization = self.request.query_params.getlist("organization")
        if organization:
            queryset = queryset.filter(organization_id__in=organization)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(organization__name__icontains=search)
                | models.Q(organization__legal_name__icontains=search)
                | models.Q(organization__edrpou__icontains=search)
                | models.Q(legal_address__icontains=search)
            )

        return queryset