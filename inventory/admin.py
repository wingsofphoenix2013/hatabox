from django.contrib import admin

from .models import (
    InvUnit,
    InvItemCategory,
    InvItem,
    ProductFamily,
    ProductFamilyLibrary,
)


@admin.register(InvUnit)
class InvUnitAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "symbol", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "symbol")
    ordering = ("sort_order", "name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(InvItemCategory)
class InvItemCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("sort_order", "name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(InvItem)
class InvItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "internal_code",
        "name",
        "category",
        "unit",
        "qr_item",
        "is_active",
        "image",
    )
    list_filter = ("is_active", "qr_item", "category", "unit")
    search_fields = ("internal_code", "name", "description")
    autocomplete_fields = ("category", "unit")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")


class ProductFamilyLibraryInline(admin.TabularInline):
    model = ProductFamilyLibrary
    extra = 0
    fields = (
        "name",
        "attachment_type",
        "file",
        "is_active",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")
    show_change_link = True


@admin.register(ProductFamily)
class ProductFamilyAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "developer", "is_active")
    list_filter = ("developer", "is_active")
    search_fields = ("code", "name", "description")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProductFamilyLibraryInline]


@admin.register(ProductFamilyLibrary)
class ProductFamilyLibraryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "product_family",
        "attachment_type",
        "is_active",
        "file",
    )
    list_filter = ("attachment_type", "is_active", "product_family")
    search_fields = (
        "name",
        "description",
        "product_family__code",
        "product_family__name",
    )
    autocomplete_fields = ("product_family",)
    ordering = ("name", "id")
    readonly_fields = ("created_at", "updated_at")