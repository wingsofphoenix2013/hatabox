from django.contrib import admin
from .models import Brand, Country


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    search_fields = ("name", "code")