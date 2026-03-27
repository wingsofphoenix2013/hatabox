from django.contrib import admin
from .models import Vendor, VendorItem


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "tax_type", "is_active")
    search_fields = ("name",)


@admin.register(VendorItem)
class VendorItemAdmin(admin.ModelAdmin):
    list_display = ("vendor", "item", "is_active")
    search_fields = ("vendor__name", "item__name")