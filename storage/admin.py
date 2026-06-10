from django.contrib import admin

from .models import (
    StorageLocation,
    StoragePlace,
    StoragePlaceEvent,
)
from .services.default_place import set_default_storage_place


@admin.action(description="Зробити місцем за замовчуванням")
def make_default_storage_place(modeladmin, request, queryset):
    if queryset.count() != 1:
        modeladmin.message_user(
            request,
            "Потрібно вибрати рівно одне місце зберігання.",
            level="ERROR",
        )
        return

    storage_place = queryset.first()
    set_default_storage_place(storage_place)

    modeladmin.message_user(
        request,
        "Місце зберігання встановлено як місце за замовчуванням.",
    )


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
        "is_default",
    )
    actions = (
        make_default_storage_place,
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
    
@admin.register(StoragePlaceEvent)
class StoragePlaceEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "storage_place",
        "event_type",
        "created_by",
        "created_at",
    )
    list_filter = (
        "event_type",
        "created_at",
    )
    search_fields = (
        "storage_place__address",
        "storage_place__code",
        "comment",
    )
    autocomplete_fields = (
        "storage_place",
        "created_by",
    )
    readonly_fields = (
        "storage_place",
        "event_type",
        "payload",
        "created_by",
        "created_at",
        "comment",
    )