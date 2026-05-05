from django.contrib import admin

from .models import (
    Organization,
    CommercialOrganization,
    MilitaryOrganization,
    CharityOrganization,
    Person,
    OrganizationPosition,
    OrganizationPersonAssignment,
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
    
@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = (
        "last_name",
        "first_name",
        "middle_name",
        "birth_day",
        "birth_month",
        "birth_year",
        "phone_1",
        "phone_1_type",
        "phone_2",
        "phone_2_type",
        "is_active",
    )
    search_fields = (
        "last_name",
        "first_name",
        "middle_name",
        "phone_1",
        "phone_2",
        "comment",
    )
    list_filter = (
        "is_active",
        "phone_1_type",
        "phone_2_type",
        "birth_month",
    )


@admin.register(OrganizationPosition)
class OrganizationPositionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
    )
    search_fields = (
        "name",
    )
    list_filter = (
        "is_active",
    )


@admin.register(OrganizationPersonAssignment)
class OrganizationPersonAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "person",
        "organization",
        "position",
        "is_current",
    )
    search_fields = (
        "person__last_name",
        "person__first_name",
        "person__middle_name",
        "organization__name",
        "organization__legal_name",
        "organization__edrpou",
        "position__name",
    )
    list_filter = (
        "is_current",
        "organization",
        "position",
    )
    autocomplete_fields = (
        "person",
        "organization",
        "position",
    )