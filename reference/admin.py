from django.contrib import admin
from .models import Brand, Country, ExternalOrderStatus, ExternalOrderPaymentStatus, TaxType


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    search_fields = ("name", "code")


@admin.register(ExternalOrderStatus)
class ExternalOrderStatusAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "sort_order", "is_active")
    search_fields = ("name", "code")
    ordering = ("sort_order",)

@admin.register(ExternalOrderPaymentStatus)
class ExternalOrderPaymentStatusAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "sort_order", "is_active")
    search_fields = ("name", "code")
    ordering = ("sort_order",)
    
@admin.register(TaxType)
class TaxTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_vat_payer",
        "is_profit_tax_payer",
        "sort_order",
        "is_active",
    )
    search_fields = ("name", "code")
    ordering = ("sort_order",)