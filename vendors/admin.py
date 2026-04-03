from django.contrib import admin
from .models import Vendor, VendorItem


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "tax_type", "is_active", "logo")
    search_fields = ("code", "name")
    list_filter = ("tax_type", "is_active")


@admin.register(VendorItem)
class VendorItemAdmin(admin.ModelAdmin):
    list_display = ("vendor", "item", "brand", "country_of_origin", "is_active")
    search_fields = ("vendor__name", "item__name", "brand__name")
    list_filter = ("vendor", "brand", "country_of_origin", "is_active")