from django.contrib import admin
from django.utils import timezone

from .models import InvUnit, InvItemCategory, InvItem


@admin.register(InvUnit)
class InvUnitAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "symbol", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "symbol")
    ordering = ("sort_order", "name")
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not obj.created_at:
            obj.created_at = timezone.now()
        obj.updated_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(InvItemCategory)
class InvItemCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("sort_order", "name")
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not obj.created_at:
            obj.created_at = timezone.now()
        obj.updated_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(InvItem)
class InvItemAdmin(admin.ModelAdmin):
    list_display = ("id", "internal_code", "name", "category", "unit", "qr_item", "is_active", "image")
    list_filter = ("is_active", "qr_item", "category", "unit")
    search_fields = ("internal_code", "name", "description")
    autocomplete_fields = ("category", "unit")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not obj.created_at:
            obj.created_at = timezone.now()
        obj.updated_at = timezone.now()
        super().save_model(request, obj, form, change)