from django.contrib import admin

from .models import (
    Organization,
    CommercialOrganization,
    MilitaryOrganization,
    CharityOrganization,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "legal_name", "type", "edrpou", "is_active")
    search_fields = ("name", "legal_name", "edrpou")
    list_filter = ("type", "is_active")


@admin.register(CommercialOrganization)
class CommercialOrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "tax_type",
        "ipn",
    )
    search_fields = (
        "organization__name",
        "organization__legal_name",
        "organization__edrpou",
        "ipn",
        "legal_address",
    )
    list_filter = (
        "tax_type",
        "organization__type",
        "organization__is_active",
    )


@admin.register(MilitaryOrganization)
class MilitaryOrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "a_code",
        "military_type",
        "military_branch",
        "military_corps",
    )
    search_fields = (
        "organization__name",
        "organization__legal_name",
        "organization__edrpou",
        "a_code",
    )
    list_filter = (
        "military_type",
        "military_branch",
        "military_corps",
        "organization__is_active",
    )


@admin.register(CharityOrganization)
class CharityOrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "legal_address",
    )
    search_fields = (
        "organization__name",
        "organization__legal_name",
        "organization__edrpou",
        "legal_address",
    )
    list_filter = (
        "organization__type",
        "organization__is_active",
    )