from django.contrib import admin
from .models import Vendor, VendorItem


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "website", "tax_type", "is_active", "logo")
    search_fields = ("code", "name")
    list_filter = ("tax_type", "is_active")


@admin.register(VendorItem)
class VendorItemAdmin(admin.ModelAdmin):
    list_display = (
        "vendor",
        "vendor_sku",
        "name",
        "item",
        "brand",
        "country_of_origin",
        "is_active",
    )
    search_fields = (
        "vendor__name",
        "vendor_sku",
        "name",
        "item__name",
        "item__internal_code",
        "brand__name",
    )
    list_filter = ("vendor", "brand", "country_of_origin", "is_active")