from django.contrib import admin

from .models import WarehouseLocation, WarehouseStoragePlace, WarehouseUnit


@admin.register(WarehouseLocation)
class WarehouseLocationAdmin(admin.ModelAdmin):
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
    
@admin.register(WarehouseStoragePlace)
class WarehouseStoragePlaceAdmin(admin.ModelAdmin):
    list_display = (
        "place_type",
        "code",
        "get_display_name",
        "location",
        "parent",
        "is_active",
    )
    search_fields = (
        "code",
        "name",
        "comment",
        "qr_code",
    )
    list_filter = (
        "place_type",
        "location",
        "is_active",
    )
    autocomplete_fields = (
        "location",
        "parent",
    )
    readonly_fields = (
        "code",
        "qr_code",
    )

@admin.register(WarehouseUnit)
class WarehouseUnitAdmin(admin.ModelAdmin):
    list_display = (
        "inventory_item",
        "quantity",
        "location",
        "storage_place",
        "source_receipt_item",
        "source_order_item",
        "is_active",
    )
    search_fields = (
        "inventory_item__internal_code",
        "inventory_item__name",
    )
    list_filter = (
        "is_active",
        "inventory_item__unit",
        "location",
    )
    autocomplete_fields = (
        "inventory_item",
        "location",
        "storage_place",
        "source_receipt_item",
        "source_order_item",
    )