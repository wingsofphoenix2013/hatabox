from django.contrib import admin

from .models import StorageLocation, StoragePlace


@admin.register(StoragePlace)
class StoragePlaceAdmin(admin.ModelAdmin):
    list_display = (
        "address",
        "place_type",
        "code",
        "location",
        "parent",
        "is_default",
        "is_active",
    )
    search_fields = (
        "address",
        "code",
        "name",
        "comment",
    )
    list_filter = (
        "place_type",
        "location",
        "is_default",
        "is_active",
    )
    autocomplete_fields = (
        "location",
        "parent",
    )
    readonly_fields = (
        "code",
        "address",
    )


@admin.register(StorageLocation)
class StorageLocationAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "address",
        "is_active",
    )
    search_fields = (
        "code",
        "name",
        "address",
        "comment",
    )
    list_filter = (
        "is_active",
    )
    readonly_fields = (
        "code",
    )