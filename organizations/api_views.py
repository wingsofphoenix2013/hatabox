from django.db import models
from django.db.models import Prefetch

from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import ModelViewSet

from .models import (
    Organization,
    CommercialOrganization,
    MilitaryOrganization,
    CharityOrganization,
    Person,
    OrganizationPosition,
    OrganizationPersonAssignment,
)
from .serializers import (
    OrganizationListSerializer,
    OrganizationSerializer,
    CommercialOrganizationSerializer,
    MilitaryOrganizationSerializer,
    CharityOrganizationSerializer,
    PersonSerializer,
    OrganizationPositionSerializer,
    OrganizationPersonAssignmentSerializer,
    PeopleDirectorySerializer,
)


class OrganizationViewSet(ModelViewSet):
    queryset = (
        Organization.objects
        .select_related("military_profile")
        .order_by("name", "id")
    )
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
        queryset = self.queryset.all()

        org_type = self.request.query_params.getlist("type")
        if org_type:
            queryset = queryset.filter(type__in=org_type)

        military_type = self.request.query_params.getlist("military_type")
        if military_type:
            queryset = queryset.filter(
                military_profile__military_type__in=military_type
            )

        military_branch = self.request.query_params.getlist("military_branch")
        if military_branch:
            queryset = queryset.filter(
                military_profile__military_branch__in=military_branch
            )

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=(is_active.lower() == "true"))

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(legal_name__icontains=search)
                | models.Q(edrpou__icontains=search)
                | models.Q(military_profile__a_code__icontains=search)
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
        queryset = self.queryset.all()

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
        queryset = self.queryset.all()

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
        queryset = self.queryset.all()

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
        
class PersonViewSet(ModelViewSet):
    queryset = Person.objects.order_by("last_name", "first_name", "middle_name", "id")
    serializer_class = PersonSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset.all()

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=(is_active.lower() == "true"))

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(last_name__icontains=search)
                | models.Q(first_name__icontains=search)
                | models.Q(middle_name__icontains=search)
                | models.Q(phone_1__icontains=search)
                | models.Q(phone_2__icontains=search)
                | models.Q(comment__icontains=search)
            )

        return queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class OrganizationPositionViewSet(ModelViewSet):
    queryset = OrganizationPosition.objects.order_by("name", "id")
    serializer_class = OrganizationPositionSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset.all()

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=(is_active.lower() == "true"))

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class OrganizationPersonAssignmentViewSet(ModelViewSet):
    queryset = OrganizationPersonAssignment.objects.select_related(
        "person",
        "organization",
        "position",
    ).order_by(
        "organization__name",
        "position__name",
        "person__last_name",
        "id",
    )
    serializer_class = OrganizationPersonAssignmentSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset.all()

        person = self.request.query_params.getlist("person")
        if person:
            queryset = queryset.filter(person_id__in=person)

        organization = self.request.query_params.getlist("organization")
        if organization:
            queryset = queryset.filter(organization_id__in=organization)

        position = self.request.query_params.getlist("position")
        if position:
            queryset = queryset.filter(position_id__in=position)

        is_current = self.request.query_params.get("is_current")
        if is_current is not None:
            queryset = queryset.filter(is_current=(is_current.lower() == "true"))

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(person__last_name__icontains=search)
                | models.Q(person__first_name__icontains=search)
                | models.Q(person__middle_name__icontains=search)
                | models.Q(organization__name__icontains=search)
                | models.Q(organization__legal_name__icontains=search)
                | models.Q(organization__edrpou__icontains=search)
                | models.Q(position__name__icontains=search)
            )

        return queryset
        
class PeopleDirectoryViewSet(ModelViewSet):
    http_method_names = ["get"]
    serializer_class = PeopleDirectorySerializer
    permission_classes = [DjangoModelPermissions]

    queryset = Person.objects.prefetch_related(
        Prefetch(
            "organization_assignments",
            queryset=OrganizationPersonAssignment.objects.filter(
                is_current=True,
            ).select_related(
                "organization",
                "position",
            ),
            to_attr="current_assignments",
        )
    ).order_by("last_name", "first_name", "middle_name", "id")

    def get_queryset(self):
        queryset = self.queryset.all()

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=(is_active.lower() == "true"))

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(last_name__icontains=search)
                | models.Q(first_name__icontains=search)
                | models.Q(middle_name__icontains=search)
                | models.Q(phone_1__icontains=search)
                | models.Q(phone_2__icontains=search)
                | models.Q(comment__icontains=search)
                | models.Q(rank__icontains=search)
                | models.Q(organization_assignments__organization__name__icontains=search)
                | models.Q(organization_assignments__position__name__icontains=search)
            ).distinct()

        return queryset