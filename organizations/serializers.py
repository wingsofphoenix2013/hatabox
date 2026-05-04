from rest_framework import serializers

from .models import (
    Organization,
    CommercialOrganization,
    MilitaryOrganization,
    CharityOrganization,
)


class OrganizationListSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "legal_name",
            "type",
            "type_display",
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