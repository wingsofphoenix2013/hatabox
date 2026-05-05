from rest_framework import serializers

from .models import (
    Organization,
    CommercialOrganization,
    MilitaryOrganization,
    CharityOrganization,
    Person,
    OrganizationPosition,
    OrganizationPersonAssignment,
)


class OrganizationListSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)

    military_type = serializers.CharField(
        source="military_profile.military_type",
        read_only=True,
        allow_null=True,
    )
    military_type_display = serializers.CharField(
        source="military_profile.get_military_type_display",
        read_only=True,
        allow_null=True,
    )
    military_branch = serializers.CharField(
        source="military_profile.military_branch",
        read_only=True,
        allow_null=True,
    )
    military_branch_display = serializers.CharField(
        source="military_profile.get_military_branch_display",
        read_only=True,
        allow_null=True,
    )
    military_corps = serializers.CharField(
        source="military_profile.military_corps",
        read_only=True,
        allow_null=True,
    )
    military_corps_display = serializers.CharField(
        source="military_profile.get_military_corps_display",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "legal_name",
            "type",
            "type_display",
            "military_type",
            "military_type_display",
            "military_branch",
            "military_branch_display",
            "military_corps",
            "military_corps_display",
        ]

class OrganizationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)

    commercial_profile_id = serializers.IntegerField(
        source="commercial_profile.id",
        read_only=True,
    )
    military_profile_id = serializers.IntegerField(
        source="military_profile.id",
        read_only=True,
    )
    charity_profile_id = serializers.IntegerField(
        source="charity_profile.id",
        read_only=True,
    )

    military_type = serializers.CharField(
        source="military_profile.military_type",
        read_only=True,
        allow_null=True,
    )
    military_type_display = serializers.CharField(
        source="military_profile.get_military_type_display",
        read_only=True,
        allow_null=True,
    )
    military_branch = serializers.CharField(
        source="military_profile.military_branch",
        read_only=True,
        allow_null=True,
    )
    military_branch_display = serializers.CharField(
        source="military_profile.get_military_branch_display",
        read_only=True,
        allow_null=True,
    )
    military_corps = serializers.CharField(
        source="military_profile.military_corps",
        read_only=True,
        allow_null=True,
    )
    military_corps_display = serializers.CharField(
        source="military_profile.get_military_corps_display",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "legal_name",
            "type",
            "type_display",
            "edrpou",
            "is_active",
            "commercial_profile_id",
            "military_profile_id",
            "charity_profile_id",
            "military_type",
            "military_type_display",
            "military_branch",
            "military_branch_display",
            "military_corps",
            "military_corps_display",
        ]

class CommercialOrganizationSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_legal_name = serializers.CharField(source="organization.legal_name", read_only=True)
    organization_type = serializers.CharField(source="organization.type", read_only=True)
    organization_edrpou = serializers.CharField(source="organization.edrpou", read_only=True)
    tax_type_name = serializers.CharField(source="tax_type.name", read_only=True)

    class Meta:
        model = CommercialOrganization
        fields = [
            "id",
            "organization",
            "organization_name",
            "organization_legal_name",
            "organization_type",
            "organization_edrpou",
            "tax_type",
            "tax_type_name",
            "ipn",
            "legal_address",
        ]


class MilitaryOrganizationSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_legal_name = serializers.CharField(source="organization.legal_name", read_only=True)
    organization_type = serializers.CharField(source="organization.type", read_only=True)
    organization_edrpou = serializers.CharField(source="organization.edrpou", read_only=True)

    military_type_display = serializers.CharField(source="get_military_type_display", read_only=True)
    military_branch_display = serializers.CharField(source="get_military_branch_display", read_only=True)
    military_corps_display = serializers.CharField(source="get_military_corps_display", read_only=True)

    class Meta:
        model = MilitaryOrganization
        fields = [
            "id",
            "organization",
            "organization_name",
            "organization_legal_name",
            "organization_type",
            "organization_edrpou",
            "a_code",
            "military_type",
            "military_type_display",
            "military_branch",
            "military_branch_display",
            "military_corps",
            "military_corps_display",
        ]


class CharityOrganizationSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_legal_name = serializers.CharField(source="organization.legal_name", read_only=True)
    organization_type = serializers.CharField(source="organization.type", read_only=True)
    organization_edrpou = serializers.CharField(source="organization.edrpou", read_only=True)

    class Meta:
        model = CharityOrganization
        fields = [
            "id",
            "organization",
            "organization_name",
            "organization_legal_name",
            "organization_type",
            "organization_edrpou",
            "legal_address",
        ]
        
class PersonSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="__str__", read_only=True)
    phone_1_type_display = serializers.CharField(source="get_phone_1_type_display", read_only=True)
    phone_2_type_display = serializers.CharField(source="get_phone_2_type_display", read_only=True)
    rank_display = serializers.CharField(source="get_rank_display", read_only=True)
    rank_force_type_display = serializers.CharField(source="get_rank_force_type_display", read_only=True)

    class Meta:
        model = Person
        fields = [
            "id",
            "last_name",
            "first_name",
            "middle_name",
            "full_name",
            "birth_day",
            "birth_month",
            "birth_year",
            "phone_1_type",
            "phone_1_type_display",
            "phone_1",
            "phone_2_type",
            "phone_2_type_display",
            "phone_2",
            "rank_force_type",
            "rank_force_type_display",
            "rank",
            "rank_display",
            "comment",
            "is_active",
        ]


class OrganizationPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationPosition
        fields = [
            "id",
            "name",
            "is_active",
        ]


class OrganizationPersonAssignmentSerializer(serializers.ModelSerializer):
    person_full_name = serializers.CharField(source="person.__str__", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_legal_name = serializers.CharField(source="organization.legal_name", read_only=True)
    position_name = serializers.CharField(source="position.name", read_only=True)

    class Meta:
        model = OrganizationPersonAssignment
        fields = [
            "id",
            "person",
            "person_full_name",
            "organization",
            "organization_name",
            "organization_legal_name",
            "position",
            "position_name",
            "is_current",
        ]
        
class PeopleDirectorySerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="__str__", read_only=True)

    phone_1_type_display = serializers.CharField(
        source="get_phone_1_type_display",
        read_only=True,
    )
    phone_2_type_display = serializers.CharField(
        source="get_phone_2_type_display",
        read_only=True,
    )

    rank_force_type_display = serializers.CharField(
        source="get_rank_force_type_display",
        read_only=True,
    )
    rank_display = serializers.CharField(
        source="get_rank_display",
        read_only=True,
    )

    current_organization_id = serializers.SerializerMethodField()
    current_organization_name = serializers.SerializerMethodField()
    current_position_id = serializers.SerializerMethodField()
    current_position_name = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = [
            "id",
            "last_name",
            "first_name",
            "middle_name",
            "full_name",
            "birth_day",
            "birth_month",
            "birth_year",
            "rank_force_type",
            "rank_force_type_display",
            "rank",
            "rank_display",
            "phone_1_type",
            "phone_1_type_display",
            "phone_1",
            "phone_2_type",
            "phone_2_type_display",
            "phone_2",
            "comment",
            "is_active",
            "current_organization_id",
            "current_organization_name",
            "current_position_id",
            "current_position_name",
        ]

    def _get_current_assignment(self, obj):
        assignments = getattr(obj, "current_assignments", [])
        return assignments[0] if assignments else None

    def get_current_organization_id(self, obj):
        assignment = self._get_current_assignment(obj)
        return assignment.organization_id if assignment else None

    def get_current_organization_name(self, obj):
        assignment = self._get_current_assignment(obj)
        return assignment.organization.name if assignment else None

    def get_current_position_id(self, obj):
        assignment = self._get_current_assignment(obj)
        return assignment.position_id if assignment else None

    def get_current_position_name(self, obj):
        assignment = self._get_current_assignment(obj)
        return assignment.position.name if assignment else None